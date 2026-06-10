"""
paper_trader.py
───────────────
模拟盘胜率追踪器。

逻辑：
  - 信号生成日 T：读取 history/YYYY-MM-DD.json 里的信号
  - 入场价：T+1 日开盘价（下一个交易日开盘）
  - 出场价：T+1+forward 日开盘价
  - 胜：出场价 > 入场价

状态（status）：
  - pending : 本地数据尚无 T+1 日（信号太新）
  - open    : 已入场，持仓中（尚未到出场日）
  - closed  : 已平仓，有完整盈亏结果

用法：
    python -m quant.signals.paper_trader          # 评估全部历史信号
    python -m quant.signals.paper_trader --days 30  # 只看最近 30 天信号
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

import pandas as pd

SIGNALS_DIR   = Path(__file__).parent
HISTORY_DIR   = SIGNALS_DIR / "history"
OUTPUT_FILE   = SIGNALS_DIR / "paper_trades.json"
HIST_DATA_DIR = Path(__file__).parent.parent / "data" / "historical"


def _load_price_df(code: str) -> pd.DataFrame | None:
    """读取本地 parquet，返回按日期排序的 DataFrame（含 date/open/close 列）。"""
    path = HIST_DATA_DIR / f"{code}.parquet"
    if not path.exists():
        return None
    df = pd.read_parquet(path)
    if "date" not in df.columns:
        return None
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    return df


def _find_open_after(df: pd.DataFrame, after_date: pd.Timestamp, offset: int) -> tuple[str | None, float | None]:
    """
    在 df 里找 after_date 之后第 offset 个交易日的开盘价。
    offset=1 → 第 1 个交易日（T+1），offset=forward+1 → 出场日。
    返回 (日期字符串, 开盘价) 或 (None, None)。
    """
    later = df[df["date"] > after_date].reset_index(drop=True)
    if len(later) < offset:
        return None, None
    row = later.iloc[offset - 1]
    return str(row["date"].date()), float(row["open"])


def evaluate_all(days: int | None = None) -> list[dict]:
    """
    扫描所有历史信号文件，评估每条信号的模拟盘结果。
    days: 只处理最近 N 天的信号文件（None = 全部）。
    返回 trade 列表，同时写入 paper_trades.json。
    """
    if not HISTORY_DIR.exists():
        print("历史信号目录不存在，请先运行 generate_signals()")
        return []

    # 收集历史 JSON 文件
    files = sorted(HISTORY_DIR.glob("????-??-??.json"), reverse=True)
    if days:
        files = files[:days]

    # 缓存已加载的行情数据，避免重复读盘
    price_cache: dict[str, pd.DataFrame | None] = {}

    trades: list[dict] = []

    for f in files:
        try:
            data = json.loads(f.read_text("utf-8"))
        except Exception:
            continue

        signal_date_str = data.get("trade_date") or f.stem
        try:
            signal_date = pd.Timestamp(signal_date_str)
        except Exception:
            continue

        for sig in data.get("signals", []):
            code    = sig.get("code", "")
            forward = int(sig.get("forward", 5))

            # 加载行情（缓存）
            if code not in price_cache:
                price_cache[code] = _load_price_df(code)
            df = price_cache[code]

            trade: dict = {
                "signal_date": signal_date_str,
                "code":        code,
                "name":        sig.get("name", code),
                "prob_up":     round(float(sig.get("prob_up", 0)), 4),
                "close_price": sig.get("close"),
                "forward":     forward,
                "entry_date":  None,
                "entry_price": None,
                "exit_date":   None,
                "exit_price":  None,
                "ret":         None,
                "win":         None,
                "status":      "pending",
            }

            if df is None:
                trades.append(trade)
                continue

            # 入场：T+1 开盘
            entry_date, entry_price = _find_open_after(df, signal_date, 1)
            if entry_date is None:
                trades.append(trade)   # pending
                continue

            trade["entry_date"]  = entry_date
            trade["entry_price"] = round(entry_price, 4)
            trade["status"]      = "open"

            # 出场：T+1+forward 开盘
            exit_date, exit_price = _find_open_after(df, signal_date, forward + 1)
            if exit_date is None:
                trades.append(trade)   # open (still holding)
                continue

            ret = (exit_price - entry_price) / entry_price
            trade["exit_date"]  = exit_date
            trade["exit_price"] = round(exit_price, 4)
            trade["ret"]        = round(ret, 4)
            trade["win"]        = ret > 0
            trade["status"]     = "closed"
            trades.append(trade)

    # 按信号日期排序（新→旧）
    trades.sort(key=lambda x: x["signal_date"], reverse=True)

    # 汇总统计
    closed = [t for t in trades if t["status"] == "closed"]
    summary = _compute_summary(closed)

    payload = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary":    summary,
        "trades":     trades,
    }
    OUTPUT_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), "utf-8")
    print(f"[paper_trader] 评估完成：{len(trades)} 条信号，{len(closed)} 条已结束，"
          f"胜率 {summary['win_rate_pct']:.1f}%")
    return trades


def _compute_summary(closed: list[dict]) -> dict:
    """计算汇总胜率指标（仅基于已关闭交易）。"""
    if not closed:
        return {
            "total": 0, "wins": 0, "losses": 0,
            "win_rate_pct": 0.0,
            "avg_ret_pct": 0.0,
            "best_ret_pct": 0.0,
            "worst_ret_pct": 0.0,
            "recent30_win_rate_pct": 0.0,
            "recent30_total": 0,
        }

    rets   = [t["ret"] for t in closed]
    wins   = sum(1 for r in rets if r > 0)
    total  = len(rets)
    avg_r  = sum(rets) / total

    # 最近 30 天信号
    cutoff = sorted([t["signal_date"] for t in closed])
    cutoff = cutoff[-30] if len(cutoff) >= 30 else cutoff[0]
    recent = [t for t in closed if t["signal_date"] >= cutoff]
    r30_wins  = sum(1 for t in recent if t["win"])
    r30_total = len(recent)

    return {
        "total":                total,
        "wins":                 wins,
        "losses":               total - wins,
        "win_rate_pct":         round(wins / total * 100, 1),
        "avg_ret_pct":          round(avg_r * 100, 2),
        "best_ret_pct":         round(max(rets) * 100, 2),
        "worst_ret_pct":        round(min(rets) * 100, 2),
        "recent30_win_rate_pct": round(r30_wins / r30_total * 100, 1) if r30_total else 0.0,
        "recent30_total":       r30_total,
    }


def load_paper_trades() -> dict:
    """从文件读取已计算的模拟盘结果。"""
    if not OUTPUT_FILE.exists():
        return {"updated_at": None, "summary": {}, "trades": []}
    try:
        return json.loads(OUTPUT_FILE.read_text("utf-8"))
    except Exception:
        return {"updated_at": None, "summary": {}, "trades": []}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=None, help="只评估最近 N 天")
    args = parser.parse_args()
    evaluate_all(args.days)
