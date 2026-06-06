"""
runner.py
──────────
基于模型信号做历史回测，输出绩效报告。

策略逻辑：
  - 收盘后拿到信号，次日开盘买入，持有 FORWARD_DAYS 日后平仓
  - 只做多（signal == 1）
  - 每次满仓进入（position_size=1.0），后续可扩展为仓位管理

用法：
    python -m quant.backtest.runner                    # 回测所有 ETF
    python -m quant.backtest.runner --code 510300      # 只回测单只
    python -m quant.backtest.runner --forward 5        # 5日预测模型
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")   # 无 GUI 环境下保存图片
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

from quant.data.fetch_historical import load as load_hist
from quant.features.engineer import add_features, get_feature_cols
from quant.models.trainer import add_label, load_model, FORWARD_DAYS
from quant.utils.etf_list import ETF_CODES, CODE_TO_NAME

REPORT_DIR = Path(__file__).parent.parent.parent / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

# Windows 中文字体
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


# ── 核心回测逻辑 ──────────────────────────────────────────────

def backtest_one(code: str, forward: int = FORWARD_DAYS) -> dict:
    """
    对单只 ETF 做信号回测，返回绩效指标字典。
    严格按时间顺序，只用测试集（后30%）部分，防止训练集泄露。
    """
    bundle = load_model(forward)
    model       = bundle["model"]
    feature_cols = bundle["feature_cols"]

    # 加载数据 + 特征
    df = load_hist(code)
    df = add_features(df)
    df = add_label(df, forward=forward)

    # 只取测试集部分（后30%，与训练时一致）
    split = int(len(df) * 0.7)
    df = df.iloc[split:].copy().reset_index(drop=True)

    if len(df) < forward * 2:
        return {"code": code, "error": "测试集数据不足"}

    # 模型预测
    X = df[feature_cols]
    df["signal"]   = model.predict(X)
    df["prob_up"]  = model.predict_proba(X)[:, list(model.classes_).index(1)] \
                     if 1 in model.classes_ else 0.0

    # ── 模拟收益 ─────────────────────────────────────────────
    # 信号=1 时，次日开盘买入，持有 forward 日后以开盘价卖出
    df["entry_price"] = df["open"].shift(-1)          # 次日开盘
    df["exit_price"]  = df["open"].shift(-(forward+1)) # forward日后开盘

    signal_rows = df[df["signal"] == 1].copy()
    signal_rows = signal_rows.dropna(subset=["entry_price", "exit_price"])

    if signal_rows.empty:
        return {"code": code, "error": "无做多信号"}

    signal_rows["trade_ret"] = (
        signal_rows["exit_price"] / signal_rows["entry_price"] - 1
    )

    # ── 绩效指标 ─────────────────────────────────────────────
    rets = signal_rows["trade_ret"].values
    n_trades  = len(rets)
    win_rate  = (rets > 0).mean()
    avg_ret   = rets.mean()
    total_ret = (1 + rets).prod() - 1

    # 年化夏普（假设每笔交易间隔 forward 日）
    if rets.std() > 0:
        sharpe = (avg_ret / rets.std()) * np.sqrt(252 / forward)
    else:
        sharpe = 0.0

    # 最大连续回撤
    cum    = pd.Series((1 + rets).cumprod())
    peak   = cum.cummax()
    dd     = (cum - peak) / peak
    max_dd = dd.min()

    # 基准：买入持有
    bh_ret = df["close"].iloc[-1] / df["close"].iloc[0] - 1

    result = {
        "code":       code,
        "name":       CODE_TO_NAME.get(code, code),
        "n_trades":   n_trades,
        "win_rate":   round(win_rate, 4),
        "avg_ret":    round(avg_ret, 4),
        "total_ret":  round(total_ret, 4),
        "sharpe":     round(sharpe, 3),
        "max_dd":     round(max_dd, 4),
        "bh_ret":     round(bh_ret, 4),
        "alpha":      round(total_ret - bh_ret, 4),
    }
    return result


def plot_equity(code: str, forward: int = FORWARD_DAYS):
    """绘制信号收益曲线 vs 买入持有，保存到 reports/。"""
    bundle = load_model(forward)
    model, feature_cols = bundle["model"], bundle["feature_cols"]

    df = load_hist(code)
    df = add_features(df)
    df = add_label(df, forward=forward)
    split = int(len(df) * 0.7)
    df = df.iloc[split:].copy().reset_index(drop=True)

    X = df[feature_cols]
    df["signal"] = model.predict(X)
    df["entry_price"] = df["open"].shift(-1)
    df["exit_price"]  = df["open"].shift(-(forward + 1))
    signal_rows = df[df["signal"] == 1].dropna(subset=["entry_price", "exit_price"]).copy()
    signal_rows["trade_ret"] = signal_rows["exit_price"] / signal_rows["entry_price"] - 1

    fig, axes = plt.subplots(2, 1, figsize=(12, 8))
    name = CODE_TO_NAME.get(code, code)

    # 上图：信号累计收益 vs 买入持有
    ax1 = axes[0]
    if not signal_rows.empty:
        cum_signal = (1 + signal_rows["trade_ret"]).cumprod()
        ax1.plot(range(len(cum_signal)), cum_signal.values, label="模型信号", color="steelblue")
    bh_norm = df["close"] / df["close"].iloc[0]
    ax1.plot(df.index / len(df) * (len(signal_rows) if not signal_rows.empty else 1),
             bh_norm.values, label="买入持有", color="orange", alpha=0.7)
    ax1.set_title(f"{name}（{code}）回测收益曲线  |  预测 {forward} 日")
    ax1.set_ylabel("累计净值")
    ax1.legend()
    ax1.grid(alpha=0.3)

    # 下图：每笔交易收益
    ax2 = axes[1]
    if not signal_rows.empty:
        colors = ["green" if r > 0 else "red" for r in signal_rows["trade_ret"]]
        ax2.bar(range(len(signal_rows)), signal_rows["trade_ret"].values, color=colors, alpha=0.7)
    ax2.axhline(0, color="black", linewidth=0.8)
    ax2.set_title("逐笔收益")
    ax2.set_ylabel("收益率")
    ax2.grid(alpha=0.3)

    plt.tight_layout()
    path = REPORT_DIR / f"backtest_{code}_fwd{forward}.png"
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"  图表已保存：{path}")


# ── 批量回测 ──────────────────────────────────────────────────

def backtest_all(codes: list[str] = ETF_CODES, forward: int = FORWARD_DAYS):
    print(f"\n=== 批量回测：预测 {forward} 日信号 ===\n")
    results = []
    for code in codes:
        try:
            r = backtest_one(code, forward)
            results.append(r)
            if "error" in r:
                print(f"  {code} ✗  {r['error']}")
            else:
                print(f"  {r['name']:12s}  交易次数:{r['n_trades']:3d}  "
                      f"胜率:{r['win_rate']:.1%}  "
                      f"总收益:{r['total_ret']:+.1%}  "
                      f"夏普:{r['sharpe']:.2f}  "
                      f"最大回撤:{r['max_dd']:.1%}  "
                      f"超额:{r['alpha']:+.1%}")
        except Exception as e:
            print(f"  {code} ✗  {e}")

    # 汇总
    valid = [r for r in results if "error" not in r]
    if valid:
        summary = pd.DataFrame(valid).set_index("code")
        csv_path = REPORT_DIR / f"backtest_summary_fwd{forward}.csv"
        summary.to_csv(csv_path, encoding="utf-8-sig")
        print(f"\n汇总报告已保存：{csv_path}")
        print(f"\n── 全市场平均（{len(valid)} 只）──")
        print(f"  平均胜率：{summary['win_rate'].mean():.1%}")
        print(f"  平均总收益：{summary['total_ret'].mean():+.1%}")
        print(f"  平均夏普：{summary['sharpe'].mean():.2f}")
        print(f"  平均超额收益：{summary['alpha'].mean():+.1%}")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--code",    type=str, default=None)
    parser.add_argument("--forward", type=int, default=FORWARD_DAYS)
    parser.add_argument("--plot",    action="store_true", help="输出收益曲线图")
    args = parser.parse_args()

    codes = [args.code] if args.code else ETF_CODES

    if len(codes) == 1 and args.plot:
        plot_equity(codes[0], args.forward)
    else:
        backtest_all(codes, args.forward)
        if args.plot:
            for code in codes[:5]:   # 只画前5只，避免太多图
                try:
                    plot_equity(code, args.forward)
                except Exception:
                    pass
