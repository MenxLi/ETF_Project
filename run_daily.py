"""
run_daily.py
─────────────
每日收盘后的主入口脚本（多用户版）。

执行顺序：
  1. 校准动态阈值
  2. 生成次日做多信号候选池（全局，与用户无关）
  3. 生成卖出信号（扫描所有用户持仓）
  4. 加载用户列表
  5. 逐用户生成建议并推送邮件

每个阶段独立 try/except + 指数退避重试，任意环节失败不阻断后续。
结构化日志写入 logs/daily_YYYY-MM-DD.jsonl。

Windows 任务计划配置：
  触发器：每天 15:35（收盘后5分钟）
  程序：  D:\AI_PROJECT\.venv\Scripts\python.exe
  参数：  D:\AI_PROJECT\run_daily.py
  起始于：D:\AI_PROJECT
"""

import json
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

BEIJING  = ZoneInfo("Asia/Shanghai")
LOG_DIR  = Path(__file__).parent / "logs"

MAX_RETRIES = 3      # 每阶段最多重试次数
BASE_DELAY  = 5.0    # 首次重试等待秒数；指数退避序列：5 → 10 → 20


def is_trading_day() -> bool:
    """简单判断：周一至周五（不排除节假日）。"""
    return datetime.now(BEIJING).weekday() < 5


# ─── 结构化日志 ──────────────────────────────────────────────────────────────

def _write_log(record: dict) -> None:
    """追加一行 JSON 到 logs/daily_YYYY-MM-DD.jsonl。"""
    LOG_DIR.mkdir(exist_ok=True)
    date_str = datetime.now(BEIJING).strftime("%Y-%m-%d")
    log_file = LOG_DIR / f"daily_{date_str}.jsonl"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


# ─── 重试执行器 ──────────────────────────────────────────────────────────────

def run_with_retry(fn, stage: str, max_retries: int = MAX_RETRIES,
                   base_delay: float = BASE_DELAY):
    """
    执行 fn()，失败时指数退避重试至多 max_retries 次。
    返回 (fn_result, success: bool)。
    任何异常均被捕获——不会向调用方传播。
    """
    last_exc: Exception | None = None
    last_tb:  str | None = None
    t_start = time.monotonic()

    for attempt in range(max_retries + 1):
        try:
            result = fn()
            elapsed = round(time.monotonic() - t_start, 2)
            retry_note = f"（重试 {attempt} 次）" if attempt else ""
            print(f"  ✓ {stage}{retry_note}  [{elapsed}s]")
            _write_log({
                "ts":         datetime.now(BEIJING).isoformat(),
                "stage":      stage,
                "status":     "ok",
                "duration_s": elapsed,
                "retries":    attempt,
            })
            return result, True

        except Exception as exc:
            last_exc = exc
            last_tb  = traceback.format_exc()
            if attempt < max_retries:
                delay = base_delay * (2 ** attempt)
                print(f"  ! {stage} 失败（第 {attempt + 1}/{max_retries + 1} 次），"
                      f"{delay:.0f}s 后重试：{exc}")
                time.sleep(delay)

    elapsed = round(time.monotonic() - t_start, 2)
    print(f"  ✗ {stage} 最终失败（已重试 {max_retries} 次）：{last_exc}")
    _write_log({
        "ts":         datetime.now(BEIJING).isoformat(),
        "stage":      stage,
        "status":     "fail",
        "duration_s": elapsed,
        "retries":    max_retries,
        "error":      str(last_exc),
        "traceback":  last_tb,
    })
    return None, False


# ─── 主流程 ──────────────────────────────────────────────────────────────────

def main():
    run_ts = datetime.now(BEIJING)
    print(f"\n{'='*50}")
    print(f"  ETF 量化日报  {run_ts:%Y-%m-%d %H:%M:%S}")
    print(f"{'='*50}\n")

    _write_log({"ts": run_ts.isoformat(), "stage": "run_start", "status": "start"})

    if not is_trading_day():
        print("今日非交易日（周末），跳过。")
        _write_log({"ts": datetime.now(BEIJING).isoformat(),
                    "stage": "run_end", "status": "skip", "reason": "non_trading_day"})
        sys.exit(0)

    # 延迟导入，避免模块级副作用影响启动
    from quant.signals.generator   import generate_signals
    from quant.signals.sell_generator import generate_sell_signals
    from quant.signals.notifier    import push_daily_report
    from quant.signals.calibrator  import calibrate
    from quant.portfolio.manager   import load_users, advise_for_user
    from quant.models.trainer      import FORWARD_DAYS

    stage_ok: dict[str, bool] = {}

    # ── 1. 校准动态阈值 ──────────────────────────────────────────────────────
    print("Step 1/5  校准动态阈值...")
    _, stage_ok["calibrate"] = run_with_retry(calibrate, "校准动态阈值")

    # ── 2. 全局生成做多信号候选池 ────────────────────────────────────────────
    print("\nStep 2/5  生成做多信号候选池...")
    signals, stage_ok["buy_signals"] = run_with_retry(
        lambda: generate_signals(forward=FORWARD_DAYS),
        "生成做多信号",
    )
    price_map = {s["code"]: s["close"] for s in signals} if signals else {}

    # ── 3. 生成卖出信号 ──────────────────────────────────────────────────────
    print("\nStep 3/5  生成卖出信号...")
    _, stage_ok["sell_signals"] = run_with_retry(generate_sell_signals, "生成卖出信号")

    # ── 4. 加载用户列表 ──────────────────────────────────────────────────────
    print("\nStep 4/5  加载用户列表...")
    users, stage_ok["load_users"] = run_with_retry(load_users, "加载用户列表")
    if users:
        print(f"  找到 {len(users)} 个活跃用户")

    # ── 5. 逐用户推送 ────────────────────────────────────────────────────────
    print("\nStep 5/5  生成建议并推送...\n")
    users_ok:   list[str] = []
    users_fail: list[str] = []

    if not stage_ok["buy_signals"]:
        print("  [跳过] 做多信号生成失败，无法推送邮件报告。")
        _write_log({"ts": datetime.now(BEIJING).isoformat(),
                    "stage": "push_all", "status": "skip",
                    "reason": "buy_signals_failed"})
    elif not stage_ok["load_users"] or not users:
        print("  [跳过] 用户列表加载失败，无法推送邮件报告。")
        _write_log({"ts": datetime.now(BEIJING).isoformat(),
                    "stage": "push_all", "status": "skip",
                    "reason": "load_users_failed"})
    else:
        for user in users:
            print(f"  ── 处理用户：{user.name} ──")

            def _push(u=user):
                advised, portfolio = advise_for_user(signals, u, price_map)
                push_daily_report(
                    advised,
                    forward=FORWARD_DAYS,
                    portfolio=portfolio,
                    email=u.email,
                )

            _, ok = run_with_retry(
                _push,
                f"推送邮件[{user.name}]",
                max_retries=2,
                base_delay=10.0,
            )
            (users_ok if ok else users_fail).append(user.name)

    # ── 汇总 ────────────────────────────────────────────────────────────────
    failed_stages = [k for k, v in stage_ok.items() if not v]
    overall = "ok" if not failed_stages and not users_fail else "partial"
    _write_log({
        "ts":            datetime.now(BEIJING).isoformat(),
        "stage":         "run_summary",
        "status":        overall,
        "failed_stages": failed_stages,
        "users_ok":      users_ok,
        "users_fail":    users_fail,
    })

    print(f"\n{'─'*50}")
    if not failed_stages and not users_fail:
        print("  全部完成，无错误。")
    else:
        if failed_stages:
            print(f"  失败阶段：{', '.join(failed_stages)}")
        if users_fail:
            print(f"  推送失败用户：{', '.join(users_fail)}")
        date_str = run_ts.strftime("%Y-%m-%d")
        print(f"  详细错误见 logs/daily_{date_str}.jsonl")
    print(f"{'─'*50}\n")


if __name__ == "__main__":
    main()
