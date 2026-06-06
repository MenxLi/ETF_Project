"""
run_daily.py
─────────────
每日收盘后的主入口脚本（多用户版）。

执行顺序：
  1. 检查今天是否为交易日（周一至周五）
  2. 校准动态阈值
  3. 生成次日做多信号候选池（全局，与用户无关）
  4. 遍历 portfolios/users.json 中的所有 active 用户：
       a. 加载该用户持仓
       b. 生成持仓感知建议
       c. 推送到该用户专属 Server酱 Key

Windows 任务计划配置：
  触发器：每天 15:35（收盘后5分钟）
  程序：  D:\AI_PROJECT\.venv\Scripts\python.exe
  参数：  D:\AI_PROJECT\run_daily.py
  起始于：D:\AI_PROJECT
"""

import sys
from datetime import datetime
from zoneinfo import ZoneInfo

BEIJING = ZoneInfo("Asia/Shanghai")


def is_trading_day() -> bool:
    """简单判断：周一至周五（不排除节假日）。"""
    return datetime.now(BEIJING).weekday() < 5


def main():
    now = datetime.now(BEIJING)
    print(f"\n{'='*50}")
    print(f"  ETF 量化日报  {now:%Y-%m-%d %H:%M:%S}")
    print(f"{'='*50}\n")

    if not is_trading_day():
        print("今日非交易日（周末），跳过。")
        sys.exit(0)

    from quant.signals.generator import generate_signals
    from quant.signals.notifier import push_daily_report
    from quant.signals.calibrator import calibrate
    from quant.portfolio.manager import load_users, advise_for_user
    from quant.models.trainer import FORWARD_DAYS

    # 1. 校准动态阈值
    print("Step 1/4  校准动态阈值...")
    calibrate()

    # 2. 全局生成信号候选池（与用户无关）
    print("Step 2/4  生成信号候选池...")
    signals = generate_signals(forward=FORWARD_DAYS)
    price_map = {s["code"]: s["close"] for s in signals}

    # 3. 加载用户列表
    print("Step 3/4  加载用户列表...")
    users = load_users()
    print(f"  找到 {len(users)} 个活跃用户")

    # 4. 逐用户推送
    print("Step 4/4  生成建议并推送...\n")
    for user in users:
        print(f"  ── 处理用户：{user.name} ──")
        advised, portfolio = advise_for_user(signals, user, price_map)
        push_daily_report(
            advised,
            forward=FORWARD_DAYS,
            portfolio=portfolio,
            email=user.email,
        )

    print("\n全部完成。")


if __name__ == "__main__":
    main()
