"""
run_intraday.py
────────────────
盘中价格监控入口（每 30 分钟由 Windows 任务计划调用）。

执行逻辑：
  1. 判断当前是否为交易日（周一至周五）
  2. 判断是否在交易时段（09:30–11:30 / 13:00–15:00）
  3. 调用 price_monitor.run_monitor()，检查所有用户持仓的止损止盈

Windows 任务计划配置（由 setup_scheduler.ps1 自动注册）：
  程序：  D:\AI_PROJECT\.venv\Scripts\python.exe
  参数：  run_intraday.py
  起始于：D:\AI_PROJECT
  触发器：每个工作日 09:30 / 10:00 / 10:30 / 11:00 / 13:00 / 13:30 / 14:00 / 14:30
"""

import sys
from datetime import datetime, time
from zoneinfo import ZoneInfo

BEIJING = ZoneInfo("Asia/Shanghai")

# 交易时段
SESSIONS = [
    (time(9, 30),  time(11, 30)),
    (time(13, 0),  time(15, 0)),
]


def is_trading_day() -> bool:
    return datetime.now(BEIJING).weekday() < 5   # 周一至周五


def in_trading_session() -> bool:
    now = datetime.now(BEIJING).time()
    return any(start <= now <= end for start, end in SESSIONS)


def main():
    now = datetime.now(BEIJING)
    print(f"\n[盘中监控] {now:%Y-%m-%d %H:%M:%S}")

    if not is_trading_day():
        print("  非交易日（周末），跳过。")
        sys.exit(0)

    if not in_trading_session():
        now_t = now.time()
        print(f"  当前 {now_t.strftime('%H:%M')} 不在交易时段，跳过。")
        sys.exit(0)

    from quant.signals.price_monitor import run_monitor
    new_count = run_monitor()
    print(f"\n  完成，新增告警 {new_count} 条。")


if __name__ == "__main__":
    main()
