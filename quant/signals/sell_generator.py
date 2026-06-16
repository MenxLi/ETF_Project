"""
sell_generator.py
──────────────────
每日收盘后运行，扫描所有用户持仓，生成卖出信号候选列表。

触发条件（优先级从高到低，任一满足即生成信号）：
  STOP_LOSS    浮亏 >= stop_loss 阈值（默认 5%）
  TAKE_PROFIT  浮盈 >= take_profit 阈值（默认 8%）
  MODEL_SELL   模型 prob_down >= sell_prob_threshold（默认 55%）

技术面预警（不单独触发，只作为辅助说明附在 reason 里）：
  RSI > 75 超买、MACD 死叉、跌破 20 日均线

输出文件：quant/signals/sell_candidates.json
  {
    "generated_at": "...",
    "trade_date":   "...",
    "users": {
      "<user_id>": [ { sell_signal_dict }, ... ]
    }
  }

用法：
    python -m quant.signals.sell_generator
"""

import json
import math
from datetime import datetime
from pathlib import Path

import pandas as pd

from quant.data.fetch_historical import load as load_hist
from quant.features.engineer import add_features, get_feature_cols
from quant.models.trainer import load_model
from quant.signals.generator import update_data, load_model_config
from quant.portfolio.manager import load_users, load_portfolio, User
from quant.utils.etf_list import CODE_TO_NAME

SIGNALS_DIR       = Path(__file__).parent
SELL_CANDIDATES   = SIGNALS_DIR / "sell_candidates.json"
PORTFOLIOS_DIR    = Path(__file__).parent.parent.parent / "portfolios"
USERS_FILE        = PORTFOLIOS_DIR / "users.json"


# ── 工具函数 ──────────────────────────────────────────────────

def _clean(obj):
    """递归清理 NaN/Inf，确保 JSON 可序列化。"""
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_clean(i) for i in obj]
    return obj


def _tech_warnings(last_row) -> list[str]:
    """从最新一行特征提取技术面预警标签（辅助信息，不作为触发条件）。"""
    warnings = []
    def _f(col):
        v = last_row.get(col)
        return float(v) if v is not None and not pd.isna(v) else None

    rsi = _f("rsi_14")
    if rsi is not None and rsi > 75:
        warnings.append(f"RSI {rsi:.0f} · 超买区，注意回调风险")

    macd_hist = _f("macd_hist")
    if macd_hist is not None and macd_hist < 0:
        warnings.append("MACD 柱线翻负 · 短期动能走弱")

    ma_dev = _f("ma_dev_20")
    if ma_dev is not None and ma_dev < -0.02:
        warnings.append(f"价格偏离20日均线 {ma_dev:.1%} · 趋势偏弱")

    ema_cross = _f("ema_cross_5_20")
    if ema_cross is not None and ema_cross < 0:
        warnings.append("EMA5 < EMA20 · 短期死叉")

    return warnings


# ── 核心：单只 ETF 模型预测 ───────────────────────────────────

def _predict_one(code: str, bundle: dict) -> dict | None:
    """
    对单只 ETF 运行模型，返回 prob_down、prob_up、close、indicators 等。
    失败返回 None。
    """
    try:
        df = update_data(code)
        df = add_features(df)
        if len(df) < 5:
            return None

        model        = bundle["model"]
        feature_cols = bundle["feature_cols"]
        classes      = list(model.classes_)

        row   = df.iloc[[-1]]
        X     = row[feature_cols]
        proba = model.predict_proba(X)[0]
        proba_map = {int(c): float(p) for c, p in zip(classes, proba)}

        last = df.iloc[-1]
        def _f(col, d=3):
            v = last.get(col)
            return round(float(v), d) if v is not None and not pd.isna(v) else None

        return {
            "prob_down": round(proba_map.get(-1, 0.0), 4),
            "prob_up":   round(proba_map.get(1,  0.0), 4),
            "prob_flat": round(proba_map.get(0,  0.0), 4),
            "close":     round(float(df["close"].iloc[-1]), 4),
            "pct_chg":   round(float(df["pct_chg"].iloc[-1]), 2),
            "date":      str(df["date"].iloc[-1].date()),
            "indicators": {
                "rsi_14":          _f("rsi_14",  1),
                "rsi_6":           _f("rsi_6",   1),
                "macd_hist":       _f("macd_hist", 5),
                "ma_dev_20":       _f("ma_dev_20", 4),
                "ema_cross_5_20":  _f("ema_cross_5_20", 5),
                "vol_ratio":       _f("vol_ratio", 2),
                "boll_pos":        _f("boll_pos",  3),
            },
            "_last_row": last,   # 内部用，序列化前会删掉
        }
    except Exception as e:
        print(f"  [{code}] 预测失败：{e}")
        return None


# ── 主函数 ────────────────────────────────────────────────────

def generate_sell_signals() -> dict:
    """
    扫描所有活跃用户持仓，生成卖出信号候选列表。
    返回 { user_id: [sell_signal, ...] } 字典，同时写入 sell_candidates.json。
    """
    cfg              = load_model_config()
    stop_loss        = float(cfg.get("stop_loss",          0.05))
    take_profit      = float(cfg.get("take_profit",        0.08))
    sell_prob_thresh = float(cfg.get("sell_prob_threshold", 0.55))

    print(f"[卖出信号] 止损={stop_loss:.0%}  止盈={take_profit:.0%}  "
          f"模型空头门槛={sell_prob_thresh:.0%}")

    # ── 1. 读取所有用户，收集持仓中的唯一 ETF 代码 ──────────
    if not USERS_FILE.exists():
        print("[卖出信号] 未找到用户文件，跳过")
        return {}

    users_raw = json.loads(USERS_FILE.read_text("utf-8"))
    active_users = [u for u in users_raw if u.get("active", True)]

    all_codes: set[str] = set()
    user_portfolios: dict[str, object] = {}

    for u_raw in active_users:
        u_model = User(
            id=u_raw["id"], name=u_raw["name"],
            email=u_raw.get("email", ""),
            portfolio_file=u_raw["portfolio_file"],
            active=True,
        )
        portfolio = load_portfolio(u_model)
        user_portfolios[u_raw["id"]] = (u_model, portfolio)
        for pos in portfolio.positions:
            all_codes.add(pos.code)

    if not all_codes:
        print("[卖出信号] 所有用户均无持仓，跳过")
        return {}

    print(f"[卖出信号] 共 {len(active_users)} 个用户，"
          f"持仓涉及 {len(all_codes)} 只 ETF，开始预测…")

    # ── 2. 对持仓 ETF 跑模型（数据更新复用 update_data）────────
    bundle = load_model()
    predictions: dict[str, dict] = {}

    for code in sorted(all_codes):
        pred = _predict_one(code, bundle)
        if pred is not None:
            predictions[code] = pred
            print(f"  {code}  prob_down={pred['prob_down']:.1%}  "
                  f"prob_up={pred['prob_up']:.1%}  close={pred['close']}")

    # ── 3. 逐用户生成卖出信号 ────────────────────────────────
    result: dict[str, list] = {}

    for user_id, (u_model, portfolio) in user_portfolios.items():
        # 注入最新收盘价更新 current_price
        for pos in portfolio.positions:
            if pos.code in predictions:
                pos.current_price = predictions[pos.code]["close"]
            else:
                pos.current_price = pos.cost_price   # 无数据时用成本价兜底

        user_signals = []

        for pos in portfolio.positions:
            code  = pos.code
            pred  = predictions.get(code)
            pnl   = pos.unrealized_pct
            name  = pos.name or CODE_TO_NAME.get(code, code)

            trigger        = None
            trigger_reason = ""

            # 规则 1：止损（最高优先级）
            if pnl <= -stop_loss:
                trigger = "STOP_LOSS"
                trigger_reason = (
                    f"当前浮亏 {abs(pnl):.1%}，已触及止损线 {stop_loss:.0%}。"
                    f"建议及时止损，控制亏损敞口。"
                )

            # 规则 2：止盈
            elif pnl >= take_profit:
                trigger = "TAKE_PROFIT"
                trigger_reason = (
                    f"当前浮盈 {pnl:.1%}，已达止盈线 {take_profit:.0%}。"
                    f"建议考虑分批兑现，锁定收益。"
                )

            # 规则 3：模型看空
            elif pred is not None and pred["prob_down"] >= sell_prob_thresh:
                trigger = "MODEL_SELL"
                trigger_reason = (
                    f"模型看空概率 {pred['prob_down']:.1%}，"
                    f"超过阈值 {sell_prob_thresh:.0%}。"
                    f"当前浮盈亏 {'+' if pnl >= 0 else ''}{pnl:.1%}，建议关注风险。"
                )

            if trigger is None:
                continue   # 无触发条件，跳过

            # 附加技术面预警（辅助说明）
            tech_warns = []
            if pred is not None and "_last_row" in pred:
                tech_warns = _tech_warnings(pred["_last_row"])

            signal = {
                "code":           code,
                "name":           name,
                "trigger":        trigger,
                "trigger_reason": trigger_reason,
                "tech_warnings":  tech_warns,
                "cost_price":     round(pos.cost_price, 4),
                "current_price":  round(pos.current_price, 4),
                "shares":         pos.shares,
                "unrealized_pct": round(pnl, 4),
                "unrealized_pnl": round(pos.unrealized_pnl, 2),
                "prob_down":      pred["prob_down"] if pred else None,
                "prob_up":        pred["prob_up"]   if pred else None,
                "close":          pred["close"]      if pred else pos.current_price,
                "pct_chg":        pred["pct_chg"]    if pred else 0.0,
                "date":           pred["date"]        if pred else "",
            }
            user_signals.append(signal)

        # 排序：止损 > 止盈 > 模型看空，同类按浮盈亏幅度降序
        _order = {"STOP_LOSS": 0, "TAKE_PROFIT": 1, "MODEL_SELL": 2}
        user_signals.sort(key=lambda s: (
            _order.get(s["trigger"], 9),
            -abs(s["unrealized_pct"])
        ))
        result[user_id] = user_signals
        print(f"  [{u_model.name}] {len(user_signals)} 个卖出信号")

    # ── 4. 清理内部字段 & 保存 ───────────────────────────────
    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "trade_date":   datetime.now().strftime("%Y-%m-%d"),
        "users":        result,
    }
    payload = _clean(payload)

    SELL_CANDIDATES.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[卖出信号] 已保存：{SELL_CANDIDATES}")
    return result


if __name__ == "__main__":
    res = generate_sell_signals()
    total = sum(len(v) for v in res.values())
    print(f"\n共生成 {total} 条卖出信号（{len(res)} 个用户）")
