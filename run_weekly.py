"""
run_weekly.py
──────────────
每周日自动执行：
  1. 用本周数据重训模型（使用现有超参数，不重新搜索，约 5-10 分钟）
  2. 校准动态阈值
  3. 用周五收盘数据生成周一信号候选池，并推送给所有用户

Windows 任务计划配置：
  触发器：每周日 20:00（收盘已过去足够久，数据已稳定）
  程序：  D:\AI_PROJECT\.venv\Scripts\python.exe
  参数：  D:\AI_PROJECT\run_weekly.py
  起始于：D:\AI_PROJECT
"""

import sys
from datetime import datetime
from zoneinfo import ZoneInfo

BEIJING = ZoneInfo("Asia/Shanghai")


def main():
    now = datetime.now(BEIJING)
    print(f"\n{'='*55}")
    print(f"  ETF 量化  周日例行任务  {now:%Y-%m-%d %H:%M:%S}")
    print(f"{'='*55}\n")

    # ── Step 1: 模型重训 ─────────────────────────────────────
    print("Step 1/4  模型周度重训（使用现有超参数）...")
    from quant.models.trainer import train, FORWARD_DAYS
    train(forward=FORWARD_DAYS)
    print("  重训完成。\n")

    # ── Step 2: 校准动态阈值 ─────────────────────────────────
    print("Step 2/4  校准动态阈值（基于周五市场数据）...")
    from quant.signals.calibrator import calibrate
    calibrate()
    print("  校准完成。\n")

    # ── Step 3: 生成周一信号候选池 ───────────────────────────
    # generate_signals() 会加载最新可用的收盘数据（即周五），
    # 在周日运行时自然使用周五数据，无需特殊处理。
    print("Step 3/4  生成周一信号候选池（基于周五收盘数据）...")
    from quant.signals.generator import generate_signals
    signals = generate_signals(forward=FORWARD_DAYS)
    price_map = {s["code"]: s["close"] for s in signals}
    print(f"  候选信号：{len(signals)} 只\n")

    # ── Step 4: 推送给所有用户 ───────────────────────────────
    print("Step 4/4  生成持仓建议并推送周一预报...\n")
    from quant.portfolio.manager import load_users, advise_for_user
    from quant.signals.notifier import push_daily_report
    users = load_users()
    print(f"  活跃用户：{len(users)} 人")
    for user in users:
        print(f"  ── 处理用户：{user.name} ──")
        advised, portfolio = advise_for_user(signals, user, price_map)
        push_daily_report(
            advised,
            forward=FORWARD_DAYS,
            portfolio=portfolio,
            email=user.email,
            subject_prefix="【周一预报】",
        )

    print("\n周日例行任务全部完成。")


if __name__ == "__main__":
    main()
