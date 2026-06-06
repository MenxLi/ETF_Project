"""
engineer.py
────────────
基于日线 OHLCV 计算技术指标特征，供 ML 模型使用。

特征分组：
  - 动量类：N日收益率、RSI
  - 均线类：EMA偏离度、均线金死叉信号
  - 波动率类：ATR、历史波动率、布林带位置
  - 量价类：量比、OBV变化率、价量背离
  - 趋势类：MACD差值、ADX

用法：
    from quant.features.engineer import add_features
    df = add_features(df)   # df 需含 open/high/low/close/volume 列
"""

import numpy as np
import pandas as pd


# ── 工具函数 ──────────────────────────────────────────────────

def _ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()

def _rsi(close: pd.Series, n: int = 14) -> pd.Series:
    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(n).mean()
    loss  = (-delta.clip(upper=0)).rolling(n).mean()
    rs    = gain / loss.replace(0, np.nan)
    return 100 - 100 / (1 + rs)

def _atr(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14) -> pd.Series:
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low  - close.shift()).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(n).mean()


# ── 主函数 ────────────────────────────────────────────────────

def add_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    输入含 open/high/low/close/volume 的日线 DataFrame，
    原地添加特征列，返回去掉初始 NaN 行后的 DataFrame。
    """
    df = df.copy().sort_values("date").reset_index(drop=True)
    c, h, l, v = df["close"], df["high"], df["low"], df["volume"]

    # ── 动量 ─────────────────────────────────────────────────
    for n in [5, 10, 20, 60]:
        df[f"mom_{n}"] = c.pct_change(n)           # N日收益率

    df["rsi_14"] = _rsi(c, 14)
    df["rsi_6"]  = _rsi(c, 6)

    # ── 均线偏离度 ────────────────────────────────────────────
    for n in [5, 10, 20, 60]:
        ma = c.rolling(n).mean()
        df[f"ma_dev_{n}"] = (c - ma) / ma          # 收盘价相对均线偏离

    # EMA 金死叉：EMA5 - EMA20（正=多头排列）
    df["ema_cross_5_20"]  = _ema(c, 5)  - _ema(c, 20)
    df["ema_cross_10_60"] = _ema(c, 10) - _ema(c, 60)

    # ── 波动率 ────────────────────────────────────────────────
    df["atr_14"]    = _atr(h, l, c, 14)
    df["atr_pct"]   = df["atr_14"] / c              # ATR 相对值，消除价格量纲

    df["hvol_10"]   = c.pct_change().rolling(10).std()   # 历史波动率 10日
    df["hvol_20"]   = c.pct_change().rolling(20).std()

    # 布林带位置：(close - 下轨) / 带宽，0=下轨，1=上轨
    boll_mid   = c.rolling(20).mean()
    boll_std   = c.rolling(20).std()
    boll_upper = boll_mid + 2 * boll_std
    boll_lower = boll_mid - 2 * boll_std
    boll_width = (boll_upper - boll_lower).replace(0, np.nan)
    df["boll_pos"]   = (c - boll_lower) / boll_width     # 0~1，越高越靠近上轨
    df["boll_width"] = boll_width / boll_mid              # 带宽相对值（衡量震荡强度）

    # ── 量价 ──────────────────────────────────────────────────
    vol_ma20 = v.rolling(20).mean().replace(0, np.nan)
    df["vol_ratio"]  = v / vol_ma20                  # 量比（相对20日均量）
    df["vol_ma5_dev"]= v.rolling(5).mean() / vol_ma20 - 1

    # OBV（能量潮）变化率
    obv = (np.sign(c.diff()) * v).cumsum()
    df["obv_chg_5"]  = obv.pct_change(5)

    # 价量背离：价涨量缩 → 负值（潜在反转信号）
    df["pv_div_5"] = c.pct_change(5) - v.pct_change(5)

    # ── MACD ──────────────────────────────────────────────────
    ema12 = _ema(c, 12)
    ema26 = _ema(c, 26)
    macd_line   = ema12 - ema26
    signal_line = _ema(macd_line, 9)
    df["macd"]        = macd_line / c               # 归一化
    df["macd_signal"] = signal_line / c
    df["macd_hist"]   = (macd_line - signal_line) / c

    # ── 去除 NaN 行（前60行指标未收敛）────────────────────────
    feature_cols = [col for col in df.columns
                    if col not in ("date", "open", "high", "low", "close",
                                   "volume", "amount", "turnover", "pct_chg",
                                   "code", "name")]
    df = df.dropna(subset=feature_cols).reset_index(drop=True)
    return df


def get_feature_cols(df: pd.DataFrame) -> list[str]:
    """返回特征列名列表（排除元数据列）。"""
    exclude = {"date", "open", "high", "low", "close", "volume",
               "amount", "turnover", "pct_chg", "code", "name", "label"}
    return [c for c in df.columns if c not in exclude]
