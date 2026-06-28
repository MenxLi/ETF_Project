"""
quant/data/tushare_client.py
─────────────────────────────
Tushare Pro 统一调用封装。

全局单例，提供：
  - 单次初始化（避免各模块重复 set_token / pro_api()）
  - 请求最小间隔限速（MIN_INTERVAL，Tushare Pro 有调用频率上限）
  - 单次调用超时（CALL_TIMEOUT，用 ThreadPoolExecutor 实现）
  - 指数退避重试（BASE_DELAY × 2^attempt，网络抖动自动恢复）

对外只暴露一个函数：

    from quant.data.tushare_client import pro_bar
    df = pro_bar(ts_code="510300.SH", asset="FD", adj="qfq",
                 start_date="20230101", end_date="20231231", freq="D")

参数与原生 ts.pro_bar 完全相同，返回值相同（DataFrame 或 None）。
"""

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from typing import TypeVar, ParamSpec, Callable
import tushare as ts
from functools import wraps

log = logging.getLogger(__name__)

# ── 可调参数 ──────────────────────────────────────────────────
MIN_INTERVAL = 0.5   # 两次调用之间最小间隔（秒）；Tushare 免费版建议 ≥ 0.3s
CALL_TIMEOUT = 30    # 单次调用超时（秒）；网络卡死时强制放弃
MAX_RETRIES  = 3     # 失败后最多重试次数（不含首次）
BASE_DELAY   = 2.0   # 首次重试等待（秒），指数退避序列：2 → 4 → 8


# ── 单例客户端 ─────────────────────────────────────────────────

class RateLimiter:
    """Tushare Pro 单例封装，限速 + 超时 + 退避重试。"""

    _rate_lock: threading.Lock
    _init_lock: threading.Lock

    def __init__(self):
        self._last_call = 0.0
        self._rate_lock = threading.Lock()

    def _throttle(self) -> None:
        """等待至距上次调用满 MIN_INTERVAL 秒，然后更新时间戳。"""
        with self._rate_lock:
            wait = MIN_INTERVAL - (time.monotonic() - self._last_call)
            if wait > 0:
                time.sleep(wait)
            self._last_call = time.monotonic()

_limiter = RateLimiter()
P = ParamSpec("P")
R = TypeVar("R")

def rate_limited(limiter: RateLimiter):
    """装饰器：对函数调用加上限速 + 超时 + 退避重试。"""
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            code_hint = kwargs.get("ts_code", "?")
            last_exc: Exception | None = None

            for attempt in range(MAX_RETRIES + 1):
                limiter._throttle()
                try:
                    with ThreadPoolExecutor(max_workers=1) as ex:
                        result = ex.submit(func, *args, **kwargs).result(timeout=CALL_TIMEOUT)
                    return result
                except FuturesTimeout:
                    last_exc = TimeoutError(
                        f"[RateLimit] {func.__name__} 超时（>{CALL_TIMEOUT}s）[{code_hint}]"
                    )
                except Exception as exc:
                    last_exc = exc

                if attempt < MAX_RETRIES:
                    delay = BASE_DELAY * (2 ** attempt)
                    log.warning(
                        "[RateLimit] %s 失败（%d/%d），%.0fs 后重试：%s",
                        code_hint, attempt + 1, MAX_RETRIES + 1, delay, last_exc,
                    )
                    time.sleep(delay)

            log.error(
                "[RateLimit] %s 最终失败（已重试 %d 次）：%s",
                code_hint, MAX_RETRIES, last_exc,
            )
            assert last_exc is not None
            raise last_exc

        return wrapper
    return decorator


# ── 模块级公共接口 ────────────────────────────────────────────

pro_bar = rate_limited(_limiter)(ts.pro_bar)