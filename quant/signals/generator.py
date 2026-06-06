"""
generator.py
─────────────
每日收盘后运行，拉取最新行情，生成次日做多信号清单。

流程：
  1. 用 yfinance 拉取所有 ETF 最新数据（增量追加到历史文件）
  2. 计算技术特征
  3. 模型预测，过滤低置信度信号
  4. 返回信号列表，供推送模块使用

用法：
    python -m quant.signals.generator          # 生成今日信号并打印
    python -m quant.signals.generator --push   # 生成后直接推送微信
"""

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import yfinance as yf

from quant.data.fetch_historical import load as load_hist, SAVE_DIR
from quant.features.engineer import add_features, get_feature_cols
from quant.models.trainer import load_model, FORWARD_DAYS
from quant.utils.etf_list import ETF_CODES, CODE_TO_NAME, _yf_code

# 默认信号过滤阈值（可通过 model_config.json 覆盖）
PROB_THRESHOLD = 0.50

# 默认黑名单（可通过 model_config.json 覆盖）
_DEFAULT_BLACKLIST = ["159869", "159766", "159928"]   # 新能源车、旅游、消费

# 候选池文件路径（盘中确认模块读取）
SIGNALS_DIR = Path(__file__).parent.parent.parent / "signals"
SIGNALS_DIR.mkdir(parents=True, exist_ok=True)
CANDIDATE_FILE = SIGNALS_DIR / "candidates.json"

# 模型参数配置文件（管理员通过 Web 界面修改）
MODEL_CONFIG_FILE = Path(__file__).parent / "model_config.json"

# 历史档案目录（每日生成一个 JSON，供看板查阅）
HISTORY_DIR = Path(__file__).parent / "history"

_CONFIG_DEFAULTS: dict = {
    "prob_threshold": PROB_THRESHOLD,
    "blacklist":      _DEFAULT_BLACKLIST,
    "threshold_overrides": {},
}


def load_model_config() -> dict:
    """读取模型配置，不存在时返回默认值。"""
    if MODEL_CONFIG_FILE.exists():
        try:
            saved = json.loads(MODEL_CONFIG_FILE.read_text("utf-8"))
            return {**_CONFIG_DEFAULTS, **saved}
        except Exception:
            pass
    return _CONFIG_DEFAULTS.copy()


def update_data(code: str) -> pd.DataFrame:
    """
    增量更新单只 ETF 数据：
    读取本地历史文件，拉取最近 10 个交易日补充，去重后保存。
    """
    try:
        existing = load_hist(code)
        last_date = existing["date"].max()
        start = (last_date + timedelta(days=1)).strftime("%Y-%m-%d")
    except FileNotFoundError:
        existing = pd.DataFrame()
        start = (datetime.today() - timedelta(days=365 * 3)).strftime("%Y-%m-%d")

    end = datetime.today().strftime("%Y-%m-%d")

    if start > end:
        return existing  # 已是最新，无需更新

    yf_code = _yf_code(code)
    ticker = yf.Ticker(yf_code)
    new_df = ticker.history(start=start, end=end, auto_adjust=True)

    if new_df.empty:
        return existing

    new_df = new_df.reset_index().rename(columns={
        "Date": "date", "Open": "open", "High": "high",
        "Low": "low", "Close": "close", "Volume": "volume",
    })
    keep = [c for c in ["date", "open", "high", "low", "close", "volume"] if c in new_df.columns]
    new_df = new_df[keep].copy()
    new_df["date"] = pd.to_datetime(new_df["date"]).dt.tz_localize(None)
    new_df["pct_chg"] = new_df["close"].pct_change() * 100
    new_df["code"] = code
    new_df["name"] = CODE_TO_NAME.get(code, "")

    if not existing.empty:
        combined = pd.concat([existing, new_df], ignore_index=True)
    else:
        combined = new_df

    combined = combined.drop_duplicates("date").sort_values("date").reset_index(drop=True)
    path = SAVE_DIR / f"{code}.parquet"
    combined.to_parquet(path, index=False)
    return combined


def generate_signals(forward: int = FORWARD_DAYS,
                     prob_threshold: float | None = None) -> list[dict]:
    """
    更新数据 → 计算特征 → 预测 → 返回信号列表。
    每个信号是一个 dict，按做多概率降序排列。
    prob_threshold 为 None 时从 model_config.json 读取。
    """
    cfg = load_model_config()
    if prob_threshold is None:
        prob_threshold = float(cfg.get("prob_threshold", PROB_THRESHOLD))
    blacklist = set(cfg.get("blacklist", _DEFAULT_BLACKLIST))

    bundle = load_model(forward)
    model        = bundle["model"]
    feature_cols = bundle["feature_cols"]
    classes      = list(model.classes_)

    print(f"[{datetime.now():%H:%M:%S}] 更新行情数据（概率门槛={prob_threshold:.0%}，黑名单={len(blacklist)}只）...")
    signals = []
    errors  = []

    for code in ETF_CODES:
        if code in blacklist:
            continue
        try:
            df = update_data(code)
            df = add_features(df)

            if len(df) < 5:
                continue

            row = df.iloc[[-1]]
            X   = row[feature_cols]

            proba  = model.predict_proba(X)[0]
            proba_map = {int(c): float(p) for c, p in zip(classes, proba)}
            signal = int(model.predict(X)[0])
            prob_up = proba_map.get(1, 0.0)

            if signal == 1 and prob_up >= prob_threshold:
                last = df.iloc[-1]
                # 提取关键技术指标，供前端展示解释
                def _f(col, decimals=3):
                    v = last.get(col)
                    return round(float(v), decimals) if v is not None and not pd.isna(v) else None

                indicators = {
                    "rsi_14":       _f("rsi_14",  1),
                    "rsi_6":        _f("rsi_6",   1),
                    "vol_ratio":    _f("vol_ratio", 2),
                    "macd_hist":    _f("macd_hist", 5),
                    "boll_pos":     _f("boll_pos",  3),
                    "ma_dev_20":    _f("ma_dev_20", 4),
                    "mom_5":        _f("mom_5",  4),
                    "mom_20":       _f("mom_20", 4),
                    "hvol_20":      _f("hvol_20", 4),
                    "ema_cross_5_20": _f("ema_cross_5_20", 5),
                }
                signals.append({
                    "code":       code,
                    "name":       CODE_TO_NAME.get(code, code),
                    "signal":     signal,
                    "prob_up":    round(prob_up, 4),
                    "prob_flat":  round(proba_map.get(0, 0.0), 4),
                    "prob_down":  round(proba_map.get(-1, 0.0), 4),
                    "close":      round(float(df["close"].iloc[-1]), 4),
                    "pct_chg":    round(float(df["pct_chg"].iloc[-1]), 2),
                    "date":       str(df["date"].iloc[-1].date()),
                    "forward":    forward,
                    "indicators": indicators,
                })
        except Exception as e:
            errors.append(f"{code}: {e}")

    signals.sort(key=lambda x: x["prob_up"], reverse=True)

    if errors:
        print(f"  [{len(errors)} 只更新失败]")
    print(f"  信号生成完成：{len(signals)} 个做多信号")

    # 保存候选池供盘中确认模块使用
    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "trade_date":   datetime.now().strftime("%Y-%m-%d"),
        "signals":      signals,
    }
    CANDIDATE_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  候选池已保存：{CANDIDATE_FILE}")

    # 历史档案：每日写一份，不覆盖（同一天多次运行只保留最新）
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    date_str     = datetime.now().strftime("%Y-%m-%d")
    history_file = HISTORY_DIR / f"{date_str}.json"
    history_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  历史档案已保存：{history_file}")

    return signals


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--forward",   type=int,   default=FORWARD_DAYS)
    parser.add_argument("--threshold", type=float, default=PROB_THRESHOLD)
    parser.add_argument("--push",      action="store_true", help="生成后推送微信")
    args = parser.parse_args()

    signals = generate_signals(args.forward, args.threshold)

    if not signals:
        print("\n今日无满足条件的做多信号。")
    else:
        print(f"\n{'─'*60}")
        print(f"  次日做多信号（预测 {args.forward} 日涨幅 > 2%）")
        print(f"{'─'*60}")
        for s in signals:
            bar = "█" * int(s["prob_up"] * 20)
            print(f"  {s['name']:12s} {s['code']}  "
                  f"做多概率: {s['prob_up']:.1%}  {bar}")
        print(f"{'─'*60}")

    if args.push:
        from quant.signals.notifier import push_daily_report
        push_daily_report(signals, forward=args.forward)
