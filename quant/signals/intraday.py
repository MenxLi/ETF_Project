"""
intraday.py
────────────
盘中4个关键节点：读取日线候选池 + 实时行情，双重确认后推送。

4个节点定义：
  NODE_OPEN   09:25  集合竞价结束，判断开盘强弱
  NODE_AMEND  11:25  上午尾声，趋势持续性确认
  NODE_PM     13:05  下午开盘，午后延续判断
  NODE_CLOSE  14:50  尾盘，资金方向与止盈提醒

确认逻辑（需同时满足）：
  日线模型候选 + 当前节点盘中条件 → 推送

用法：
  python -m quant.signals.intraday --node open    # 手动触发某个节点
  python -m quant.signals.intraday --node amend
  python -m quant.signals.intraday --node pm
  python -m quant.signals.intraday --node close
  python -m quant.signals.intraday --auto         # 自动判断当前时间对应节点
"""

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import akshare as ak
import pandas as pd

from quant.signals.generator import CANDIDATE_FILE
from quant.signals.notifier import push_intraday_report
from quant.signals.calibrator import load_thresholds
from quant.utils.etf_list import CODE_TO_NAME


def _broadcast(node_label: str, confirmed: list[dict]):
    """将盘中确认邮件发送给 users.json 中所有活跃用户。"""
    try:
        from quant.portfolio.manager import load_users
        users = load_users()
    except Exception as e:
        print(f"[推送] 无法加载用户列表: {e}")
        return

    for user in users:
        push_intraday_report(node_label, confirmed, email=user.email)

BEIJING = ZoneInfo("Asia/Shanghai")

# ── 节点定义 ──────────────────────────────────────────────────
NODES = {
    "open":  {"label": "开盘竞价",   "time": "09:25"},
    "amend": {"label": "午盘收盘前", "time": "11:25"},
    "pm":    {"label": "下午开盘",   "time": "13:05"},
    "close": {"label": "尾盘",       "time": "14:50"},
}

# 自动节点判断：距离各节点时间最近且未超过15分钟
NODE_MINUTES = {
    "open":  9 * 60 + 25,
    "amend": 11 * 60 + 25,
    "pm":    13 * 60 + 5,
    "close": 14 * 60 + 50,
}


# ── 实时行情拉取 ──────────────────────────────────────────────

def fetch_realtime() -> pd.DataFrame:
    """拉取全量 ETF 实时行情。"""
    try:
        df = ak.fund_etf_spot_em()
        df = df.rename(columns={
            "代码": "code", "名称": "name", "最新价": "price",
            "涨跌幅": "pct_chg", "成交量": "volume", "成交额": "amount",
            "开盘价": "open_price", "最高价": "high", "最低价": "low",
            "昨收": "prev_close", "量比": "vol_ratio",
        })
        df["code"] = df["code"].astype(str)
        return df
    except Exception as e:
        print(f"[实时行情] 拉取失败: {e}")
        return pd.DataFrame()


def fetch_mock_realtime() -> pd.DataFrame:
    """
    用最近一个交易日的历史数据模拟实时行情，供非交易时段测试使用。
    用昨日 OHLCV 填充实时行情字段。
    """
    from quant.data.fetch_historical import load as load_hist
    from quant.utils.etf_list import ETF_CODES

    rows = []
    for code in ETF_CODES:
        try:
            df = load_hist(code)
            if len(df) < 2:
                continue
            last  = df.iloc[-1]   # 模拟"当日"
            prev  = df.iloc[-2]   # 模拟"昨收"
            pct   = (last["close"] - prev["close"]) / prev["close"] * 100
            vol_ratio = (last["volume"] / df["volume"].rolling(20).mean().iloc[-1]
                         if df["volume"].rolling(20).mean().iloc[-1] > 0 else 1.0)
            rows.append({
                "code":       code,
                "name":       last.get("name", code),
                "price":      last["close"],
                "pct_chg":    round(pct, 2),
                "open_price": last["open"],
                "high":       last["high"],
                "low":        last["low"],
                "prev_close": prev["close"],
                "vol_ratio":  round(vol_ratio, 2),
                "volume":     last["volume"],
            })
        except Exception:
            continue

    df = pd.DataFrame(rows)
    print(f"[Mock] 使用历史数据模拟实时行情，共 {len(df)} 只 ETF")
    return df


def get_realtime_row(code: str, rt_df: pd.DataFrame) -> dict | None:
    """从实时行情 DataFrame 中取出单只 ETF 数据。"""
    rows = rt_df[rt_df["code"] == code]
    if rows.empty:
        return None
    r = rows.iloc[0]
    return {
        "price":     _safe_float(r.get("price")),
        "pct_chg":   _safe_float(r.get("pct_chg")),
        "open_price": _safe_float(r.get("open_price")),
        "prev_close": _safe_float(r.get("prev_close")),
        "vol_ratio":  _safe_float(r.get("vol_ratio")),
        "high":       _safe_float(r.get("high")),
        "low":        _safe_float(r.get("low")),
    }


def _safe_float(val) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


# ── 各节点确认逻辑 ────────────────────────────────────────────

def check_open(rt: dict, thr: dict) -> tuple[bool, str]:
    """9:25 开盘竞价：涨幅 > 下限 且 量比 > 动态门槛"""
    pct   = rt["pct_chg"]
    vol_r = rt["vol_ratio"]
    ok    = pct > thr["open_pct_min"] and vol_r > thr["open_vol_ratio_min"]
    reason = f"开盘{pct:+.2f}%，量比{vol_r:.2f}x（门槛{thr['open_vol_ratio_min']}x）"
    return ok, reason


def check_amend(rt: dict, thr: dict) -> tuple[bool, str]:
    """11:25 午盘前：涨幅在动态区间内"""
    pct = rt["pct_chg"]
    lo, hi = thr["amend_pct_min"], thr["amend_pct_max"]
    ok  = lo < pct < hi
    reason = f"上午{pct:+.2f}%（有效区间{lo:.2f}%~{hi:.2f}%）"
    return ok, reason


def check_pm(rt: dict, thr: dict) -> tuple[bool, str]:
    """13:05 下午开盘：上午收涨且涨幅未过热"""
    pct    = rt["pct_chg"]
    price  = rt["price"]
    open_p = rt["open_price"]
    above_open = price > open_p if open_p > 0 else False
    ok = above_open and thr["pm_pct_min"] <= pct < thr["pm_pct_max"]
    reason = f"现价{price:.2f}，高于开盘{open_p:.2f}，涨幅{pct:+.2f}%"
    return ok, reason


def check_close(rt: dict, thr: dict) -> tuple[bool, str]:
    """
    14:50 尾盘双向判断：
      - 强势持续（涨幅 > 动态门槛，量比 > 1）
      - 从高点回落超过动态回撤阈值
    """
    pct   = rt["pct_chg"]
    vol_r = rt["vol_ratio"]
    high  = rt["high"]
    price = rt["price"]
    dd_thr = thr["close_dd_threshold"]
    strong = thr["close_strong_pct"]

    if pct > strong and vol_r > 1.0:
        return True, f"尾盘强势 {pct:+.2f}% 量比{vol_r:.2f}x"
    elif high > 0 and (high - price) / high * 100 > dd_thr:
        return True, f"⚠️ 尾盘回落>{dd_thr:.1f}% 高点{high:.2f} 现价{price:.2f}，注意止盈"
    return False, f"尾盘平淡 {pct:+.2f}%"


CHECK_FUNC = {
    "open":  check_open,
    "amend": check_amend,
    "pm":    check_pm,
    "close": check_close,
}


# ── 候选池读取 ────────────────────────────────────────────────

def load_candidates() -> list[dict]:
    """读取昨日收盘后生成的候选池。"""
    if not CANDIDATE_FILE.exists():
        print("[候选池] 文件不存在，请先运行 generator.py")
        return []
    data = json.loads(CANDIDATE_FILE.read_text(encoding="utf-8"))
    candidates = data.get("signals", [])
    trade_date = data.get("trade_date", "")
    print(f"[候选池] 读取 {len(candidates)} 只候选，生成于 {data.get('generated_at','')}")
    return candidates


# ── 主逻辑 ────────────────────────────────────────────────────

def run_node(node: str, mock: bool = False):
    """执行指定节点的盘中确认并推送。mock=True 时使用历史数据模拟。"""
    assert node in NODES, f"未知节点: {node}，可选: {list(NODES)}"
    label = NODES[node]["label"]
    now_str = datetime.now(BEIJING).strftime("%H:%M")
    print(f"\n[{now_str}] 节点：{label}{'  [MOCK模式]' if mock else ''}")

    candidates = load_candidates()
    if not candidates:
        return

    print("[实时行情] 拉取中...")
    rt_df = fetch_mock_realtime() if mock else fetch_realtime()
    if rt_df.empty:
        print("[实时行情] 拉取失败，跳过")
        return

    check_fn = CHECK_FUNC[node]
    thr = load_thresholds()
    print(f"[阈值] 量比门槛:{thr['open_vol_ratio_min']}  "
          f"午盘区间:[{thr['amend_pct_min']},{thr['amend_pct_max']}]%  "
          f"尾盘强势:{thr['close_strong_pct']}%  "
          f"尾盘回落:{thr['close_dd_threshold']}%")
    confirmed = []

    for c in candidates:
        code = c["code"]
        rt = get_realtime_row(code, rt_df)
        if rt is None:
            continue
        ok, reason = check_fn(rt, thr)
        if ok:
            confirmed.append({**c, "rt": rt, "reason": reason})

    print(f"[确认] {len(confirmed)}/{len(candidates)} 只通过节点确认")

    if not confirmed:
        print(f"  无确认信号，本节点不推送")
        return

    print(f"\n[推送] {label} 确认 {len(confirmed)} 只，发送邮件中...")
    _broadcast(label, confirmed)


def auto_node(mock: bool = False):
    """根据当前时间自动选择最近的节点。"""
    now = datetime.now(BEIJING)
    now_min = now.hour * 60 + now.minute
    for node, mins in NODE_MINUTES.items():
        if abs(now_min - mins) <= 15:
            print(f"[自动] 当前时间 {now.strftime('%H:%M')}，匹配节点：{NODES[node]['label']}")
            run_node(node, mock=mock)
            return
    print(f"[自动] 当前时间 {now.strftime('%H:%M')} 不在任何节点窗口内（±15分钟），跳过")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--node", choices=list(NODES), help="指定节点")
    parser.add_argument("--auto", action="store_true",  help="自动匹配当前节点")
    parser.add_argument("--mock", action="store_true",  help="用历史数据模拟实时行情（非交易时段测试用）")
    args = parser.parse_args()

    if args.auto:
        auto_node(mock=args.mock)
    elif args.node:
        run_node(args.node, mock=args.mock)
    else:
        parser.print_help()
