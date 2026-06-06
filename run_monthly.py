"""
run_monthly.py
───────────────
每月第一个周日自动运行 Optuna 超参数搜索 + 重训。
约30-60分钟，比周度重训更彻底。
"""

from datetime import datetime
from zoneinfo import ZoneInfo

BEIJING = ZoneInfo("Asia/Shanghai")


def is_first_sunday() -> bool:
    """判断今天是否为本月第一个周日。"""
    now = datetime.now(BEIJING)
    return now.weekday() == 6 and now.day <= 7


def main():
    now = datetime.now(BEIJING)
    print(f"\n{'='*50}")
    print(f"  ETF 量化模型月度调优  {now:%Y-%m-%d %H:%M:%S}")
    print(f"{'='*50}\n")

    if not is_first_sunday():
        print("今日不是本月第一个周日，跳过月度调优。")
        print("（普通周日重训已由 run_weekly.py 处理）")
        return

    print("本月第一个周日，启动 Optuna 超参数搜索...")
    from quant.models.tuner import tune
    from quant.models.trainer import FORWARD_DAYS
    tune(forward=FORWARD_DAYS, n_trials=50)
    print("\n月度调优完成。")


if __name__ == "__main__":
    main()
