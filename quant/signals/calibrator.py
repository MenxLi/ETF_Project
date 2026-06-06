"""
calibrator.py
──────────────
根据近期历史数据自动校准盘中确认节点的动态阈值。

校准逻辑：
  - 量比阈值  = 近N日各ETF量比的 p50（市场均值水位）× 系数
  - 涨幅下限  = 近N日平均日波动率（std of pct_chg）× 0.3
  - 涨幅上限  = 近N日平均日波动率 × 3.0
  - 尾盘回落  = 近N日平均 ATR% × 0.8

每日收盘后由 run_daily.py 调用，结果保存到 signals/thresholds.json。
盘中节点从该文件读取，不再使用硬编码数字。
"""

import json
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd

from quant.data.fetch_historical import load as load_hist
from quant.utils.etf_list import ETF_CODES

SIGNALS_DIR   = Path(__file__).parent.parent.parent / "signals"
THRESHOLD_FILE = SIGNALS_DIR / "thresholds.json"
SIGNALS_DIR.mkdir(parents=True, exist_ok=True)

LOOKBACK_DAYS = 20   # 用近多少个交易日校准


def _compute_market_stats(lookback: int = LOOKBACK_DAYS) -> dict:
    """
    遍历所有 ETF 近 lookback 个交易日，
    汇总市场级别的波动率、量比分布和 ATR。
    """
    all_pct     = []   # 每日涨跌幅样本
    all_vol_r   = []   # 量比样本（用成交量代理）
    all_atr_pct = []   # ATR% 样本

    for code in ETF_CODES:
        try:
            df = load_hist(code).tail(lookback + 5)
            if len(df) < lookback:
                continue

            df = df.tail(lookback).copy()
            pct = df["pct_chg"].dropna()
            all_pct.extend(pct.tolist())

            # 量比：当日成交量 / 近20日均量
            vol_ma = df["volume"].rolling(20, min_periods=5).mean()
            vol_ratio = (df["volume"] / vol_ma.replace(0, np.nan)).dropna()
            all_vol_r.extend(vol_ratio.tolist())

            # ATR%
            hi, lo, cl = df["high"], df["low"], df["close"]
            tr = pd.concat([
                hi - lo,
                (hi - cl.shift()).abs(),
                (lo - cl.shift()).abs(),
            ], axis=1).max(axis=1)
            atr_pct = (tr / cl * 100).dropna()
            all_atr_pct.extend(atr_pct.tolist())

        except Exception:
            continue

    return {
        "pct":     np.array(all_pct),
        "vol_r":   np.array(all_vol_r),
        "atr_pct": np.array(all_atr_pct),
    }


def calibrate(lookback: int = LOOKBACK_DAYS) -> dict:
    """
    计算动态阈值，保存到文件，并返回阈值字典。
    """
    print(f"[校准] 基于近 {lookback} 个交易日数据计算动态阈值...")
    stats = _compute_market_stats(lookback)

    pct     = stats["pct"]
    vol_r   = stats["vol_r"]
    atr_pct = stats["atr_pct"]

    if len(pct) == 0:
        print("[校准] 数据不足，使用默认阈值")
        return load_thresholds()   # 返回上次或默认值

    vol_std    = float(np.std(pct))         # 市场平均日波动率（标准差）
    atr_mean   = float(np.mean(atr_pct))    # 市场平均 ATR%
    vol_r_p50  = float(np.percentile(vol_r, 50))  # 量比中位数

    thresholds = {
        "calibrated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "lookback_days": lookback,

        # ── 节点：开盘竞价 ────────────────────────────────────
        # 量比需超过近期中位数 × 1.1，略高于市场均值才算活跃
        "open_vol_ratio_min": round(max(vol_r_p50 * 1.1, 1.05), 2),
        # 涨幅 > 0 即可（竞价阶段不要求太多）
        "open_pct_min":       0.0,

        # ── 节点：午盘收盘前 ──────────────────────────────────
        # 下限：0.3个标准差，低于此视为无效涨幅
        "amend_pct_min": round(max(vol_std * 0.3, 0.15), 2),
        # 上限：3个标准差，超过此视为过热不追
        "amend_pct_max": round(min(vol_std * 3.0, 6.0),  2),

        # ── 节点：下午开盘 ────────────────────────────────────
        # 涨幅在 0 ~ 上限之间（上限同午盘）
        "pm_pct_min": 0.0,
        "pm_pct_max": round(min(vol_std * 3.0, 6.0), 2),

        # ── 节点：尾盘 ───────────────────────────────────────
        # 强势判断：涨幅 > 0.5个标准差
        "close_strong_pct":  round(max(vol_std * 0.5, 0.5), 2),
        # 回落警告：从高点回落超过 0.8 × ATR
        "close_dd_threshold": round(max(atr_mean * 0.8, 1.5), 2),

        # ── 参考信息（便于人工审查）─────────────────────────
        "_market_vol_std":   round(vol_std,   3),
        "_market_atr_mean":  round(atr_mean,  3),
        "_vol_ratio_p50":    round(vol_r_p50, 3),
    }

    THRESHOLD_FILE.write_text(
        json.dumps(thresholds, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"[校准] 完成，阈值已保存：{THRESHOLD_FILE}")
    print(f"  市场波动率(std): {thresholds['_market_vol_std']:.2f}%")
    print(f"  市场ATR均值:     {thresholds['_market_atr_mean']:.2f}%")
    print(f"  量比中位数:      {thresholds['_vol_ratio_p50']:.2f}")
    print(f"  开盘量比门槛:    {thresholds['open_vol_ratio_min']}")
    print(f"  午盘涨幅区间:    [{thresholds['amend_pct_min']}, {thresholds['amend_pct_max']}]%")
    print(f"  尾盘强势门槛:    {thresholds['close_strong_pct']}%")
    print(f"  尾盘回落门槛:    {thresholds['close_dd_threshold']}%")

    return thresholds


# 默认阈值（首次运行 / 数据不足时的兜底）
_DEFAULTS = {
    "open_vol_ratio_min":  1.2,
    "open_pct_min":        0.0,
    "amend_pct_min":       0.3,
    "amend_pct_max":       4.0,
    "pm_pct_min":          0.0,
    "pm_pct_max":          5.0,
    "close_strong_pct":    1.0,
    "close_dd_threshold":  3.0,
}


def load_thresholds() -> dict:
    """
    读取已保存的动态阈值，优先级：
      默认值 < 自动校准结果 < model_config.json 的 threshold_overrides
    """
    result = _DEFAULTS.copy()
    if THRESHOLD_FILE.exists():
        data = json.loads(THRESHOLD_FILE.read_text(encoding="utf-8"))
        result = {**result, **data}
    else:
        print("[校准] 阈值文件不存在，使用默认值（建议先运行 calibrator.py）")

    # 叠加管理员手动覆盖
    try:
        config_file = Path(__file__).parent / "model_config.json"
        if config_file.exists():
            config = json.loads(config_file.read_text("utf-8"))
            for k, v in config.get("threshold_overrides", {}).items():
                if v is not None and k in _DEFAULTS:
                    result[k] = float(v)
    except Exception:
        pass

    return result


if __name__ == "__main__":
    calibrate()
