"""
trainer.py
────────────
标签生成 + LightGBM 模型训练。

标签定义：
  未来 FORWARD_DAYS 日收益率 > THRESHOLD → 1（做多信号）
  未来 FORWARD_DAYS 日收益率 < -THRESHOLD → -1（做空/回避）
  其余 → 0（观望）
  回测时只用 1 类信号（只做多）

训练策略：
  - 按时间切分，前 70% 训练，后 30% 测试（严禁未来数据泄露）
  - 使用全部 ETF 数据合并训练（跨品种泛化）
  - GPU 加速（RTX 4070）

用法：
    python -m quant.models.trainer              # 训练并保存模型
    python -m quant.models.trainer --forward 5  # 预测5日后涨跌
"""

import argparse
import json
import pickle
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.preprocessing import label_binarize

from quant.data.fetch_historical import load as load_hist
from quant.features.engineer import add_features, get_feature_cols
from quant.utils.etf_list import ETF_CODES

MODEL_DIR = Path(__file__).parent / "saved"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

# ── 超参数 ────────────────────────────────────────────────────
FORWARD_DAYS = 5       # 预测 N 日后收益
THRESHOLD    = 0.02    # 2% 涨跌阈值（低于此视为横盘）
TRAIN_RATIO  = 0.7     # 训练集比例


# ── 标签生成 ──────────────────────────────────────────────────

def add_label(df: pd.DataFrame, forward: int = FORWARD_DAYS,
              threshold: float = THRESHOLD) -> pd.DataFrame:
    """
    添加 label 列：
      1  → 未来 forward 日涨幅 > threshold
      -1 → 未来 forward 日跌幅 > threshold
      0  → 横盘
    最后 forward 行因无未来数据会被删除。
    """
    future_ret = df["close"].shift(-forward) / df["close"] - 1
    df = df.copy()
    df["label"] = 0
    df.loc[future_ret >  threshold,  "label"] =  1
    df.loc[future_ret < -threshold,  "label"] = -1
    df = df.iloc[:-forward].copy()   # 删除尾部无标签行
    return df


# ── 数据准备 ──────────────────────────────────────────────────

def build_dataset(codes: list[str] = ETF_CODES,
                  forward: int = FORWARD_DAYS) -> pd.DataFrame:
    """加载所有 ETF，添加特征和标签，合并为一个 DataFrame。"""
    frames = []
    for code in codes:
        try:
            df = load_hist(code)
            df = add_features(df)
            df = add_label(df, forward=forward)
            frames.append(df)
        except FileNotFoundError:
            print(f"  跳过 {code}（无本地数据）")
        except Exception as e:
            print(f"  跳过 {code}：{e}")

    if not frames:
        raise RuntimeError("没有可用数据，请先运行 fetch_historical")

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.sort_values("date").reset_index(drop=True)
    print(f"数据集：{len(combined)} 行  |  "
          f"标签分布：{combined['label'].value_counts().to_dict()}")
    return combined


def time_split(df: pd.DataFrame, ratio: float = TRAIN_RATIO):
    """按时间顺序切分训练/测试集，严禁随机打乱。"""
    split = int(len(df) * ratio)
    return df.iloc[:split].copy(), df.iloc[split:].copy()


# ── 模型训练 ──────────────────────────────────────────────────

def train(forward: int = FORWARD_DAYS) -> lgb.LGBMClassifier:
    print(f"\n=== 训练模型：预测 {forward} 日涨跌 ===\n")

    df = build_dataset(forward=forward)
    train_df, test_df = time_split(df)

    feature_cols = get_feature_cols(df)
    X_train = train_df[feature_cols]
    y_train = train_df["label"]
    X_test  = test_df[feature_cols]
    y_test  = test_df["label"]

    print(f"训练集：{len(X_train)} 行  测试集：{len(X_test)} 行")
    print(f"特征数：{len(feature_cols)}\n")

    # 尝试 GPU，失败自动降级 CPU
    try:
        model = lgb.LGBMClassifier(
            n_estimators=500,
            learning_rate=0.05,
            num_leaves=63,
            max_depth=-1,
            min_child_samples=30,
            feature_fraction=0.8,
            bagging_fraction=0.8,
            bagging_freq=5,
            reg_alpha=0.1,
            reg_lambda=0.1,
            class_weight="balanced",
            device="gpu",
            verbose=-1,
        )
        model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            callbacks=[lgb.early_stopping(50, verbose=False),
                       lgb.log_evaluation(100)],
        )
        print("GPU 训练完成")
    except Exception:
        print("GPU 不可用，切换 CPU...")
        model = lgb.LGBMClassifier(
            n_estimators=500,
            learning_rate=0.05,
            num_leaves=63,
            min_child_samples=30,
            feature_fraction=0.8,
            bagging_fraction=0.8,
            bagging_freq=5,
            reg_alpha=0.1,
            reg_lambda=0.1,
            class_weight="balanced",
            verbose=-1,
        )
        model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            callbacks=[lgb.early_stopping(50, verbose=False),
                       lgb.log_evaluation(100)],
        )

    # ── 评估 ─────────────────────────────────────────────────
    y_pred = model.predict(X_test)
    print("\n── 分类报告 ──")
    print(classification_report(y_test, y_pred, target_names=["空/回避(-1)", "横盘(0)", "做多(1)"]))

    # 特征重要性 Top 10
    fi = pd.Series(model.feature_importances_, index=feature_cols).sort_values(ascending=False)
    print("── Top 10 特征重要性 ──")
    print(fi.head(10).to_string())

    # 保存带日期的版本文件
    date_str   = date.today().strftime("%Y%m%d")
    model_name = f"lgbm_forward{forward}_{date_str}.pkl"
    model_path = MODEL_DIR / model_name
    bundle     = {"model": model, "feature_cols": feature_cols,
                  "forward": forward, "threshold": THRESHOLD}
    with open(model_path, "wb") as f:
        pickle.dump(bundle, f)
    print(f"\n模型已保存：{model_path}")

    # 将新版本设为激活版本
    _set_active_model(forward, model_name)
    print(f"已激活版本：{model_name}")
    return model


_MODEL_CONFIG = MODEL_DIR.parent.parent / "signals" / "model_config.json"


def _set_active_model(forward: int, filename: str) -> None:
    """将 filename 写入 model_config.json 的 active_models[forward]。"""
    try:
        cfg = json.loads(_MODEL_CONFIG.read_text("utf-8")) if _MODEL_CONFIG.exists() else {}
    except Exception:
        cfg = {}
    cfg.setdefault("active_models", {})[str(forward)] = filename
    _MODEL_CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), "utf-8")


def load_model(forward: int = FORWARD_DAYS) -> dict:
    """
    加载模型：优先使用 model_config.json 中 active_models 指定的版本，
    不存在或出错时回退到旧式固定文件名 lgbm_forward{forward}.pkl。
    """
    # 优先：读 active_models 配置
    try:
        if _MODEL_CONFIG.exists():
            cfg = json.loads(_MODEL_CONFIG.read_text("utf-8"))
            active_file = cfg.get("active_models", {}).get(str(forward))
            if active_file:
                active_path = MODEL_DIR / active_file
                if active_path.exists():
                    with open(active_path, "rb") as f:
                        return pickle.load(f)
    except Exception:
        pass

    # 回退：旧式固定文件名（兼容存量环境）
    path = MODEL_DIR / f"lgbm_forward{forward}.pkl"
    if not path.exists():
        raise FileNotFoundError(f"模型不存在：{path}，请先运行 trainer.py")
    with open(path, "rb") as f:
        return pickle.load(f)


def predict_latest(code: str, forward: int = FORWARD_DAYS) -> dict:
    """
    对单只 ETF 最新一行数据预测，返回信号和各类概率。
    用于盘后信号生成。
    """
    bundle = load_model(forward)
    model: lgb.LGBMClassifier = bundle["model"]
    feature_cols: list = bundle["feature_cols"]

    df = load_hist(code)
    df = add_features(df)

    row = df.iloc[[-1]][feature_cols]
    proba = model.predict_proba(row)[0]
    classes = model.classes_   # [-1, 0, 1]

    proba_map = {int(c): float(p) for c, p in zip(classes, proba)}
    signal = int(model.predict(row)[0])

    return {
        "code":     code,
        "date":     str(df["date"].iloc[-1].date()),
        "signal":   signal,            # 1=做多, 0=观望, -1=回避
        "prob_up":  proba_map.get(1, 0),
        "prob_flat": proba_map.get(0, 0),
        "prob_down": proba_map.get(-1, 0),
        "forward_days": forward,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--forward", type=int, default=FORWARD_DAYS,
                        help="预测未来几日涨跌")
    args = parser.parse_args()
    train(forward=args.forward)
