"""
manager.py
───────────
多用户持仓管理：读取用户注册表 + 各用户持仓文件，
为每个用户独立生成持仓感知的交易建议。

目录结构：
  portfolios/
    users.json        ← 用户注册表
    suiy.json         ← 用户持仓文件（一人一个）
    user_002.json
    ...

建议类型：
  OPEN    新开仓（未持有）
  ADD     加仓（已持有，仓位未满）
  HOLD    观望（仓位或集中度到上限）
  REDUCE  减仓（触及止盈/止损线）
  SKIP    跳过（板块超限或现金不足）
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent.parent.parent
PORTFOLIOS_DIR = ROOT / "portfolios"
USERS_FILE     = PORTFOLIOS_DIR / "users.json"

DEFAULT_TAKE_PROFIT = 0.08
DEFAULT_STOP_LOSS   = 0.05


def _load_thresholds() -> tuple[float, float]:
    """从 model_config.json 读取止盈止损阈值，文件不存在或解析失败时返回默认值。"""
    try:
        cfg_file = ROOT / "quant" / "signals" / "model_config.json"
        if cfg_file.exists():
            cfg = json.loads(cfg_file.read_text("utf-8"))
            return float(cfg.get("take_profit", DEFAULT_TAKE_PROFIT)), \
                   float(cfg.get("stop_loss",   DEFAULT_STOP_LOSS))
    except Exception:
        pass
    return DEFAULT_TAKE_PROFIT, DEFAULT_STOP_LOSS

from quant.utils.etf_list import ETF_LIST
CATEGORY_MAP = {e["code"]: e["category"] for e in ETF_LIST}


# ── 数据模型 ──────────────────────────────────────────────────

@dataclass
class User:
    id:             str
    name:           str
    email:          str
    portfolio_file: str
    active:         bool = True


@dataclass
class Position:
    code:          str
    name:          str
    shares:        float
    cost_price:    float
    buy_date:      str
    current_price: float = 0.0

    @property
    def cost_value(self) -> float:
        return self.shares * self.cost_price

    @property
    def current_value(self) -> float:
        return self.shares * self.current_price if self.current_price > 0 else self.cost_value

    @property
    def unrealized_pnl(self) -> float:
        return self.current_value - self.cost_value

    @property
    def unrealized_pct(self) -> float:
        return self.unrealized_pnl / self.cost_value if self.cost_value > 0 else 0.0

    @property
    def category(self) -> str:
        return CATEGORY_MAP.get(self.code, "其他")


@dataclass
class Portfolio:
    user:             User
    cash:             float
    max_position_pct: float
    max_sector_pct:   float
    positions:        list[Position] = field(default_factory=list)
    updated_at:       str = ""

    @property
    def total_value(self) -> float:
        return self.cash + sum(p.current_value for p in self.positions)

    @property
    def invested_value(self) -> float:
        return sum(p.current_value for p in self.positions)

    @property
    def position_pct(self) -> float:
        return self.invested_value / self.total_value if self.total_value > 0 else 0.0

    def get_position(self, code: str) -> Optional[Position]:
        return next((p for p in self.positions if p.code == code), None)

    def sector_pct(self, category: str) -> float:
        val = sum(p.current_value for p in self.positions if p.category == category)
        return val / self.total_value if self.total_value > 0 else 0.0

    def position_weight(self, code: str) -> float:
        pos = self.get_position(code)
        return pos.current_value / self.total_value if pos and self.total_value > 0 else 0.0


# ── 读取 ──────────────────────────────────────────────────────

def load_users() -> list[User]:
    """读取用户注册表，返回所有 active 用户。"""
    if not USERS_FILE.exists():
        raise FileNotFoundError(f"用户注册表不存在：{USERS_FILE}")
    data = json.loads(USERS_FILE.read_text(encoding="utf-8"))
    user_keys = {"id", "name", "email", "portfolio_file", "active"}
    return [User(**{k: v for k, v in u.items() if k in user_keys}) for u in data if u.get("active", True)]


def load_portfolio(user: User, price_map: dict[str, float] = None) -> Portfolio:
    """读取某用户的持仓文件，注入最新价格。"""
    path = ROOT / user.portfolio_file
    if not path.exists():
        # 持仓文件不存在时返回空持仓
        print(f"  [{user.name}] 持仓文件不存在，视为空仓")
        return Portfolio(user=user, cash=0, max_position_pct=0.30,
                         max_sector_pct=0.50)

    data = json.loads(path.read_text(encoding="utf-8"))
    positions = []
    for p in data.get("positions", []):
        pos = Position(
            code=p["code"], name=p["name"],
            shares=float(p["shares"]), cost_price=float(p["cost_price"]),
            buy_date=p.get("buy_date", ""),
        )
        pos.current_price = (price_map or {}).get(p["code"], pos.cost_price)
        positions.append(pos)

    return Portfolio(
        user=user,
        cash=float(data.get("cash", 0)),
        max_position_pct=float(data.get("max_position_pct", 0.30)),
        max_sector_pct=float(data.get("max_sector_pct", 0.50)),
        positions=positions,
        updated_at=data.get("updated_at", ""),
    )


# ── 技术指标摘要（通俗解释）─────────────────────────────────

def _indicator_tags(signal: dict) -> list[str]:
    """
    从信号的 indicators 字段生成一组简短的中文标签，
    每个标签描述一个技术指标的状态，供前端展示。
    """
    ind  = signal.get("indicators") or {}
    tags = []

    # RSI
    rsi = ind.get("rsi_14")
    if rsi is not None:
        if rsi < 30:
            tags.append(f"RSI {rsi:.0f} · 超卖区，弹性大")
        elif rsi < 45:
            tags.append(f"RSI {rsi:.0f} · 偏低，上行空间充足")
        elif rsi < 60:
            tags.append(f"RSI {rsi:.0f} · 温和健康")
        elif rsi < 75:
            tags.append(f"RSI {rsi:.0f} · 偏高，追高需谨慎")
        else:
            tags.append(f"RSI {rsi:.0f} · 超买，注意风险")

    # 量比
    vol = ind.get("vol_ratio")
    if vol is not None:
        if vol >= 2.5:
            tags.append(f"量比 {vol:.1f}x · 大幅放量，资金积极进场")
        elif vol >= 1.5:
            tags.append(f"量比 {vol:.1f}x · 放量，关注度提升")
        elif vol >= 0.8:
            tags.append(f"量比 {vol:.1f}x · 成交平稳")
        else:
            tags.append(f"量比 {vol:.1f}x · 缩量，观望情绪较浓")

    # MACD 柱状线
    macd = ind.get("macd_hist")
    if macd is not None:
        if macd > 0:
            tags.append("MACD 柱翻正 · 多头动能增强")
        else:
            tags.append("MACD 柱为负 · 等待金叉信号")

    # 布林带位置
    boll = ind.get("boll_pos")
    if boll is not None:
        if boll < 0.2:
            tags.append(f"布林带下轨附近 · 历史低估区")
        elif boll < 0.4:
            tags.append(f"布林带中下方 · 支撑较强")
        elif boll < 0.65:
            tags.append(f"布林带中段 · 位置中性")
        else:
            tags.append(f"布林带中上方 · 注意上方阻力")

    # 20日动量
    mom20 = ind.get("mom_20")
    if mom20 is not None:
        pct = mom20 * 100
        if pct > 5:
            tags.append(f"20日涨 {pct:+.1f}% · 中期趋势向上")
        elif pct > 0:
            tags.append(f"20日涨 {pct:+.1f}% · 小幅上行")
        elif pct > -5:
            tags.append(f"20日跌 {pct:+.1f}% · 近期有所调整")
        else:
            tags.append(f"20日跌 {pct:+.1f}% · 近期明显调整，关注企稳")

    # EMA 金叉
    ema_x = ind.get("ema_cross_5_20")
    if ema_x is not None:
        if ema_x > 0:
            tags.append("EMA5 > EMA20 · 短期多头排列")
        else:
            tags.append("EMA5 < EMA20 · 短期偏弱")

    return tags


# ── 建议逻辑 ──────────────────────────────────────────────────

def advise(signal: dict, portfolio: Portfolio,
           take_profit: float = None,
           stop_loss:   float = None) -> dict:
    if take_profit is None or stop_loss is None:
        _tp, _sl = _load_thresholds()
        if take_profit is None:
            take_profit = _tp
        if stop_loss is None:
            stop_loss = _sl
    code     = signal["code"]
    category = CATEGORY_MAP.get(code, "其他")
    pos      = portfolio.get_position(code)

    pos_weight = portfolio.position_weight(code)
    sec_pct    = portfolio.sector_pct(category)

    if pos is not None:
        pnl = pos.unrealized_pct
        if pnl >= take_profit:
            advice = "REDUCE"
            reason = (f"您持有该ETF成本价 ¥{pos.cost_price:.3f}，当前浮盈已达 {pnl:.1%}，"
                      f"超过止盈线 {take_profit:.0%}。模型仍看好，但落袋为安是合理选择，"
                      f"可考虑分批减仓锁定收益。")
        elif pnl <= -stop_loss:
            advice = "REDUCE"
            reason = (f"您持有该ETF成本价 ¥{pos.cost_price:.3f}，当前浮亏 {abs(pnl):.1%}，"
                      f"触及止损线 {stop_loss:.0%}。即便模型继续看多，控制亏损优先，"
                      f"建议止损或减仓降低风险敞口。")
        elif pos_weight >= portfolio.max_position_pct:
            advice = "HOLD"
            reason = (f"您在该ETF的持仓占总资产 {pos_weight:.1%}，"
                      f"已达您设定的单只上限 {portfolio.max_position_pct:.0%}。"
                      f"信号仍有效，但不宜继续加仓，维持现有仓位即可。")
        elif sec_pct >= portfolio.max_sector_pct:
            advice = "HOLD"
            reason = (f"您的{category}板块整体仓位已达 {sec_pct:.1%}（上限 {portfolio.max_sector_pct:.0%}）。"
                      f"该ETF信号良好，但增加同一板块风险过于集中，建议观望。")
        else:
            pnl_str = f"浮盈 {pnl:.1%}" if pnl >= 0 else f"浮亏 {abs(pnl):.1%}"
            advice  = "ADD"
            reason  = (f"您已持有该ETF（{pnl_str}），模型今日再次发出做多信号，"
                       f"趋势仍在延续。当前仓位 {pos_weight:.1%}，未达上限 {portfolio.max_position_pct:.0%}，"
                       f"可考虑适量加仓。")
    else:
        if sec_pct >= portfolio.max_sector_pct:
            advice = "SKIP"
            reason = (f"您的{category}板块仓位已达 {sec_pct:.1%}（上限 {portfolio.max_sector_pct:.0%}）。"
                      f"这只ETF信号不错，但同一板块仓位过重不利于分散风险，本次跳过。")
        elif portfolio.position_pct >= 0.95:
            advice = "SKIP"
            reason = (f"您账户总仓位已达 {portfolio.position_pct:.1%}，可用现金不足。"
                      f"信号有效，但资金有限，建议等待其他仓位减少后再考虑。")
        else:
            advice = "OPEN"
            reason = (f"您尚未持有该ETF，模型看多信号明确（置信度 {signal['prob_up']:.1%}）。"
                      f"账户可用资金 ¥{portfolio.cash:,.0f}，{category}板块仓位"
                      f" {sec_pct:.1%}（上限 {portfolio.max_sector_pct:.0%}），"
                      f"可考虑建仓。")

    return {
        **signal,
        "advice":         advice,
        "advice_reason":  reason,
        "indicator_tags": _indicator_tags(signal),
        "holding":        pos is not None,
        "cost_price":     round(pos.cost_price, 2) if pos else None,
        "unrealized_pct": round(pos.unrealized_pct, 4) if pos else None,
        "pos_weight":     round(pos_weight, 4),
        "sector":         category,
    }


def advise_for_user(signals: list[dict], user: User,
                    price_map: dict[str, float] = None) -> tuple[list[dict], Portfolio]:
    """为单个用户生成带建议的信号列表。"""
    portfolio = load_portfolio(user, price_map)
    advised   = [advise(s, portfolio) for s in signals]
    return advised, portfolio


def advise_all_users(signals: list[dict],
                     price_map: dict[str, float] = None) -> list[tuple[User, list[dict], Portfolio]]:
    """
    遍历所有活跃用户，各自生成持仓感知建议。
    返回 [(user, advised_signals, portfolio), ...]
    """
    users   = load_users()
    results = []
    for user in users:
        advised, portfolio = advise_for_user(signals, user, price_map)
        results.append((user, advised, portfolio))
        print(f"  [{user.name}] 建议生成完成，持仓 {len(portfolio.positions)} 只")
    return results
