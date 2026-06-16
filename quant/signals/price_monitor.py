"""
price_monitor.py
─────────────────
盘中价格监控：扫描所有用户持仓，拉取实时价格，触发止损/止盈告警。

设计原则：
  - 批量拉取：一次新浪请求覆盖所有持仓 ETF，不逐只请求
  - 去重：同一用户 + 同一 ETF + 同一触发类型，当天只写一条告警
  - 只做规则检查（止损/止盈），不跑模型（模型是日线级别）
  - 告警写入 quant/signals/alerts.json，前端轮询读取

告警文件格式：
  {
    "alerts": [
      {
        "id":             "20260616_143000_suiy_510300_STOP_LOSS",
        "user_id":        "suiy",
        "user_name":      "Suiy",
        "code":           "510300",
        "name":           "沪深300ETF",
        "trigger":        "STOP_LOSS",         # STOP_LOSS | TAKE_PROFIT
        "trigger_reason": "...",
        "cost_price":     3.85,
        "current_price":  3.62,
        "unrealized_pct": -0.057,
        "timestamp":      "2026-06-16 14:30:00",
        "date":           "2026-06-16",
        "dismissed":      false
      }
    ]
  }

用法：
    python -m quant.signals.price_monitor          # 检查一次
    python -m quant.signals.price_monitor --mock   # 用昨收价模拟（测试用）
"""

import json
import urllib.request
from datetime import datetime, date
from pathlib import Path

ROOT          = Path(__file__).parent.parent.parent
ALERTS_FILE   = Path(__file__).parent / "alerts.json"
PORTFOLIOS_DIR = ROOT / "portfolios"
USERS_FILE     = PORTFOLIOS_DIR / "users.json"


# ── 新浪实时价格批量拉取 ──────────────────────────────────────

def _sina_code(code: str) -> str:
    return ("sh" if (code.startswith("5") and not code.startswith("159")) else "sz") + code


def fetch_prices_batch(codes: list[str]) -> dict[str, float]:
    """
    批量拉取新浪实时价格，返回 {code: current_price}。
    一次请求覆盖所有代码，避免频繁调用。
    失败时返回空字典。
    """
    if not codes:
        return {}

    sina_codes = ",".join(_sina_code(c) for c in codes)
    url = f"https://hq.sinajs.cn/list={sina_codes}"
    try:
        req = urllib.request.Request(url, headers={
            "Referer": "https://finance.sina.com.cn",
            "User-Agent": "Mozilla/5.0",
        })
        with urllib.request.urlopen(req, timeout=8) as resp:
            text = resp.read().decode("gbk", errors="replace")
    except Exception as e:
        print(f"[价格监控] 新浪实时行情拉取失败：{e}")
        return {}

    result: dict[str, float] = {}
    for line in text.strip().splitlines():
        # var hq_str_sh510300="沪深300ETF,open,prev_close,current,..."
        try:
            # 提取代码
            key_part = line.split("=")[0]          # var hq_str_sh510300
            raw_code = key_part.split("_")[-1]     # sh510300
            code = raw_code[2:]                    # 510300

            inner = line.split('"')[1]
            parts = inner.split(",")
            if len(parts) >= 4 and parts[3]:
                price = float(parts[3])
                if price > 0:
                    result[code] = price
        except Exception:
            continue

    print(f"[价格监控] 批量拉取 {len(codes)} 只，成功获取 {len(result)} 只实时价")
    return result


# ── 告警文件读写 ──────────────────────────────────────────────

def read_alerts() -> list[dict]:
    if not ALERTS_FILE.exists():
        return []
    try:
        return json.loads(ALERTS_FILE.read_text("utf-8")).get("alerts", [])
    except Exception:
        return []


def write_alerts(alerts: list[dict]):
    ALERTS_FILE.write_text(
        json.dumps({"alerts": alerts}, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def _dedup_key(user_id: str, code: str, trigger: str, today: str) -> str:
    return f"{today}_{user_id}_{code}_{trigger}"


# ── 配置读取 ──────────────────────────────────────────────────

def _load_thresholds() -> tuple[float, float]:
    cfg_file = Path(__file__).parent / "model_config.json"
    try:
        if cfg_file.exists():
            cfg = json.loads(cfg_file.read_text("utf-8"))
            return float(cfg.get("take_profit", 0.08)), float(cfg.get("stop_loss", 0.05))
    except Exception:
        pass
    return 0.08, 0.05


# ── 主函数 ────────────────────────────────────────────────────

def run_monitor(mock: bool = False) -> int:
    """
    扫描所有用户持仓，检查止损止盈，写入新告警。
    返回新增告警数量。
    mock=True 时用昨收价代替实时价（非交易时段测试用）。
    """
    if not USERS_FILE.exists():
        print("[价格监控] 未找到用户文件，跳过")
        return 0

    take_profit, stop_loss = _load_thresholds()
    today     = date.today().isoformat()
    now_str   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[价格监控] {now_str}  止损={stop_loss:.0%}  止盈={take_profit:.0%}"
          f"{'  [MOCK]' if mock else ''}")

    # ── 1. 读取所有用户持仓，收集唯一 ETF 代码 ──────────────
    users_raw = json.loads(USERS_FILE.read_text("utf-8"))
    active    = [u for u in users_raw if u.get("active", True)]

    user_positions: dict[str, list[dict]] = {}   # user_id -> positions list
    all_codes: set[str] = set()

    for u in active:
        pf_file = ROOT / u["portfolio_file"]
        if not pf_file.exists():
            continue
        pf = json.loads(pf_file.read_text("utf-8"))
        positions = pf.get("positions", [])
        if positions:
            user_positions[u["id"]] = {"positions": positions, "user": u}
            for pos in positions:
                all_codes.add(pos["code"])

    if not all_codes:
        print("[价格监控] 所有用户均无持仓，跳过")
        return 0

    # ── 2. 批量拉取实时价 ────────────────────────────────────
    if mock:
        # Mock 模式：用本地历史数据的最新收盘价
        from quant.data.fetch_historical import load as load_hist
        price_map: dict[str, float] = {}
        for code in all_codes:
            try:
                df = load_hist(code)
                price_map[code] = float(df["close"].iloc[-1])
            except Exception:
                pass
        print(f"[价格监控] Mock 模式，加载 {len(price_map)} 只历史收盘价")
    else:
        price_map = fetch_prices_batch(list(all_codes))

    if not price_map:
        print("[价格监控] 无实时价格数据，退出")
        return 0

    # ── 3. 读取已有告警，建立去重集合 ────────────────────────
    existing_alerts = read_alerts()
    # 清理 7 天前的旧告警，避免文件无限增长
    cutoff = sorted([today])[0]  # 实际逻辑：保留最近 7 天
    from datetime import timedelta
    cutoff_date = (date.today() - timedelta(days=7)).isoformat()
    existing_alerts = [a for a in existing_alerts if a.get("date", "") >= cutoff_date]

    dedup_set: set[str] = {
        _dedup_key(a["user_id"], a["code"], a["trigger"], a["date"])
        for a in existing_alerts
    }

    new_alerts: list[dict] = []

    # ── 4. 逐用户检查持仓 ───────────────────────────────────
    for user_id, info in user_positions.items():
        u        = info["user"]
        positions = info["positions"]

        for pos in positions:
            code       = pos["code"]
            name       = pos.get("name", code)
            cost_price = float(pos.get("cost_price", 0))
            shares     = float(pos.get("shares", 0))

            if cost_price <= 0 or shares <= 0:
                continue

            current_price = price_map.get(code)
            if current_price is None:
                continue   # 无实时价，跳过

            unrealized_pct = (current_price - cost_price) / cost_price

            # 判断触发条件
            trigger        = None
            trigger_reason = ""

            if unrealized_pct <= -stop_loss:
                trigger = "STOP_LOSS"
                trigger_reason = (
                    f"当前价 ¥{current_price:.3f}，成本价 ¥{cost_price:.3f}，"
                    f"浮亏 {abs(unrealized_pct):.1%}，已触及止损线 {stop_loss:.0%}。"
                    f"建议及时止损，控制亏损敞口。"
                )
            elif unrealized_pct >= take_profit:
                trigger = "TAKE_PROFIT"
                trigger_reason = (
                    f"当前价 ¥{current_price:.3f}，成本价 ¥{cost_price:.3f}，"
                    f"浮盈 {unrealized_pct:.1%}，已达止盈线 {take_profit:.0%}。"
                    f"建议考虑分批兑现，锁定收益。"
                )

            if trigger is None:
                continue

            # 去重检查
            dk = _dedup_key(user_id, code, trigger, today)
            if dk in dedup_set:
                continue

            alert_id = f"{today.replace('-','')}_{datetime.now().strftime('%H%M%S')}_{user_id}_{code}_{trigger}"
            alert = {
                "id":             alert_id,
                "user_id":        user_id,
                "user_name":      u.get("name", user_id),
                "code":           code,
                "name":           name,
                "trigger":        trigger,
                "trigger_reason": trigger_reason,
                "cost_price":     round(cost_price, 4),
                "current_price":  round(current_price, 4),
                "unrealized_pct": round(unrealized_pct, 4),
                "unrealized_pnl": round((current_price - cost_price) * shares, 2),
                "shares":         shares,
                "timestamp":      now_str,
                "date":           today,
                "dismissed":      False,
            }
            new_alerts.append(alert)
            dedup_set.add(dk)
            print(f"  [{u.get('name', user_id)}] {name}({code}) → {trigger}  "
                  f"{unrealized_pct:+.1%}")

    # ── 5. 保存 ─────────────────────────────────────────────
    if new_alerts:
        write_alerts(existing_alerts + new_alerts)
        print(f"[价格监控] 新增 {len(new_alerts)} 条告警，已写入 {ALERTS_FILE}")
    else:
        # 仍然写回（可能清理了旧告警）
        write_alerts(existing_alerts)
        print(f"[价格监控] 无新告警（现有 {len(existing_alerts)} 条）")

    return len(new_alerts)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--mock", action="store_true", help="用历史收盘价模拟（测试用）")
    args = parser.parse_args()
    run_monitor(mock=args.mock)
