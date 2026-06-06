"""
realtime_monitor.py
────────────────────
盘中实时行情轮询 + 信号触发推送。

逻辑：
  1. 每 INTERVAL 分钟抓一次全量 ETF 实时报价
  2. 计算当前价格相对于前日收盘的涨跌幅、量比等简单特征
  3. 如触发预设阈值 → 调用 notifier 推送提醒
  4. 将实时快照追加写入 data/realtime/<date>.parquet

用法：
    python realtime_monitor.py              # 前台运行,Ctrl+C 停止
    python realtime_monitor.py --interval 3 # 每 3 分钟轮询一次

推送配置：在项目根目录 config.py 中填写 SERVER_CHAN_KEY(微信推送)
"""

import time
import argparse
import logging
from datetime import datetime, date
from pathlib import Path
from zoneinfo import ZoneInfo

import akshare as ak
import pandas as pd

from quant.utils.etf_list import ETF_CODES, CODE_TO_NAME

# ── 配置 ──────────────────────────────────────────────────────
SAVE_DIR = Path(__file__).parent / "realtime"
SAVE_DIR.mkdir(parents=True, exist_ok=True)

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

BEIJING = ZoneInfo("Asia/Shanghai")

# 交易时段（北京时间）
SESSIONS = [
    ("09:25", "11:35"),  # 早盘（含集合竞价）
    ("12:55", "15:05"),  # 午盘
]

# 触发推送的简单阈值（后续由 ML 模型替换）
ALERT_PCT_UP   =  3.0   # 涨幅超过 3% 提醒
ALERT_PCT_DOWN = -3.0   # 跌幅超过 3% 提醒
ALERT_VOL_RATIO = 3.0   # 量比超过 3 提醒

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "realtime.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)


# ── 推送 ──────────────────────────────────────────────────────
def send_alert(title: str, content: str):
    """
    微信推送（Server酱）。
    需在 config.py 中设置 SERVER_CHAN_KEY。
    未配置时仅打印日志。
    """
    try:
        from config import SERVER_CHAN_KEY
        import urllib.request, urllib.parse
        url = f"https://sctapi.ftqq.com/{SERVER_CHAN_KEY}.send"
        data = urllib.parse.urlencode({"title": title, "desp": content}).encode()
        urllib.request.urlopen(url, data=data, timeout=5)
        log.info(f"[推送] {title}")
    except ImportError:
        log.warning(f"[推送未配置] {title} | {content}")
    except Exception as e:
        log.error(f"[推送失败] {e}")


# ── 行情抓取 ──────────────────────────────────────────────────
def fetch_realtime() -> pd.DataFrame:
    """抓取全量 ETF 实时行情，返回标准化 DataFrame。"""
    df = ak.fund_etf_spot_em()
    df = df.rename(columns={
        "代码":     "code",
        "名称":     "name",
        "最新价":   "price",
        "涨跌幅":   "pct_chg",
        "涨跌额":   "chg",
        "成交量":   "volume",
        "成交额":   "amount",
        "开盘价":   "open",
        "最高价":   "high",
        "最低价":   "low",
        "昨收":     "prev_close",
        "换手率":   "turnover",
        "量比":     "vol_ratio",
    })
    # 只保留我们关注的 ETF
    df = df[df["code"].isin(ETF_CODES)].copy()
    df["ts"] = datetime.now(BEIJING).strftime("%Y-%m-%d %H:%M:%S")
    return df


# ── 信号检测 ──────────────────────────────────────────────────
def check_alerts(df: pd.DataFrame):
    """检测简单阈值，触发推送。"""
    for _, row in df.iterrows():
        alerts = []
        try:
            pct  = float(row.get("pct_chg", 0) or 0)
            vol  = float(row.get("vol_ratio", 0) or 0)
            name = row.get("name", row["code"])

            if pct >= ALERT_PCT_UP:
                alerts.append(f"涨幅 **{pct:.2f}%**")
            if pct <= ALERT_PCT_DOWN:
                alerts.append(f"跌幅 **{pct:.2f}%**")
            if vol >= ALERT_VOL_RATIO:
                alerts.append(f"量比 **{vol:.1f}x**")

            if alerts:
                title   = f"📊 {name}（{row['code']}）异动"
                content = (
                    f"- 当前价：{row.get('price', '-')}\n"
                    f"- 触发条件：{' | '.join(alerts)}\n"
                    f"- 时间：{row['ts']}"
                )
                send_alert(title, content)
        except Exception as e:
            log.debug(f"check_alerts 行处理异常: {e}")


# ── 存储快照 ──────────────────────────────────────────────────
def save_snapshot(df: pd.DataFrame):
    today = date.today().strftime("%Y%m%d")
    path  = SAVE_DIR / f"{today}.parquet"
    if path.exists():
        existing = pd.read_parquet(path)
        df = pd.concat([existing, df], ignore_index=True)
    df.to_parquet(path, index=False)


# ── 时段判断 ──────────────────────────────────────────────────
def in_trading_session() -> bool:
    now = datetime.now(BEIJING).strftime("%H:%M")
    return any(start <= now <= end for start, end in SESSIONS)


# ── 主循环 ────────────────────────────────────────────────────
def run(interval: int = 5):
    log.info(f"实时监控启动，轮询间隔 {interval} 分钟")
    while True:
        if not in_trading_session():
            log.info("非交易时段，等待...")
            time.sleep(60)
            continue
        try:
            df = fetch_realtime()
            log.info(f"抓取 {len(df)} 只 ETF 行情")
            save_snapshot(df)
            check_alerts(df)
        except Exception as e:
            log.error(f"轮询异常: {e}")
        time.sleep(interval * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", type=int, default=5, help="轮询间隔（分钟）")
    args = parser.parse_args()
    run(args.interval)
