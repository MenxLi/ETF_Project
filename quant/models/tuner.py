"""
tuner.py
─────────
用 Optuna 自动搜索 LightGBM 最优超参数。

搜索目标：
  - 验证集 F1-score（做多类别，label=1）
  - 用时序交叉验证（TimeSeriesSplit），防止未来泄露

搜索完成后自动以最优参数重训完整模型并保存。

用法：
    python -m quant.models.tuner                    # 默认 50 次 trial
    python -m quant.models.tuner --trials 100       # 更充分的搜索
    python -m quant.models.tuner --forward 5        # 指定预测周期
"""

import argparse
import pickle
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import lightgbm as lgb
import optuna
from optuna.samplers import TPESampler
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import f1_score

from quant.models.trainer import (
    build_dataset, FORWARD_DAYS, TRAIN_RATIO, MODEL_DIR
)
from quant.features.engineer import get_feature_cols

warnings.filterwarnings("ignore")
optuna.logging.set_verbosity(optuna.logging.WARNING)


# ── 搜索空间 ──────────────────────────────────────────────────

def _suggest_params(trial: optuna.Trial) -> dict:
    return {
        "n_estimators":      trial.suggest_int("n_estimators", 200, 1000),
        "learning_rate":     trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
        "num_leaves":        trial.suggest_int("num_leaves", 20, 150),
        "max_depth":         trial.suggest_int("max_depth", 3, 12),
        "min_child_samples": trial.suggest_int("min_child_samples", 10, 80),
        "feature_fraction":  trial.suggest_float("feature_fraction", 0.5, 1.0),
        "bagging_fraction":  trial.suggest_float("bagging_fraction", 0.5, 1.0),
        "bagging_freq":      trial.suggest_int("bagging_freq", 1, 10),
        "reg_alpha":         trial.suggest_float("reg_alpha", 1e-4, 10.0, log=True),
        "reg_lambda":        trial.suggest_float("reg_lambda", 1e-4, 10.0, log=True),
        "min_split_gain":    trial.suggest_float("min_split_gain", 0.0, 1.0),
    }


# ── Objective ─────────────────────────────────────────────────

def make_objective(X: np.ndarray, y: np.ndarray, feature_cols: list):
    """返回 Optuna objective 函数（闭包）。"""
    tscv = TimeSeriesSplit(n_splits=5)

    def objective(trial: optuna.Trial) -> float:
        params = _suggest_params(trial)
        params.update({
            "class_weight": "balanced",
            "verbose":      -1,
            "n_jobs":       -1,
        })

        scores = []
        for train_idx, val_idx in tscv.split(X):
            X_tr, X_val = X[train_idx], X[val_idx]
            y_tr, y_val = y[train_idx], y[val_idx]

            model = lgb.LGBMClassifier(**params)
            model.fit(
                X_tr, y_tr,
                eval_set=[(X_val, y_val)],
                callbacks=[lgb.early_stopping(30, verbose=False)],
            )
            y_pred = model.predict(X_val)
            # 只优化做多信号（label=1）的 F1
            f1 = f1_score(y_val, y_pred, labels=[1], average="macro",
                          zero_division=0)
            scores.append(f1)

        return float(np.mean(scores))

    return objective


# ── 主流程 ────────────────────────────────────────────────────

def tune(forward: int = FORWARD_DAYS, n_trials: int = 50):
    print(f"\n=== Optuna 超参数搜索：预测 {forward} 日  |  {n_trials} 次 trial ===\n")

    # 准备数据（只用训练集部分，测试集留给最终评估）
    df = build_dataset(forward=forward)
    split = int(len(df) * TRAIN_RATIO)
    train_df = df.iloc[:split].copy()

    feature_cols = get_feature_cols(df)
    X = train_df[feature_cols].values
    y = train_df["label"].values

    print(f"搜索数据：{len(train_df)} 行  |  特征数：{len(feature_cols)}")
    print(f"标签分布：{ {k: int(v) for k, v in zip(*np.unique(y, return_counts=True))} }\n")

    # 创建 study
    study = optuna.create_study(
        direction="maximize",
        sampler=TPESampler(seed=42),
        study_name=f"lgbm_fwd{forward}",
    )

    # 进度回调
    def progress_cb(study, trial):
        if trial.number % 10 == 0 or trial.number < 5:
            print(f"  Trial {trial.number:3d}  |  "
                  f"当前: {trial.value:.4f}  |  "
                  f"最优: {study.best_value:.4f}")

    study.optimize(
        make_objective(X, y, feature_cols),
        n_trials=n_trials,
        callbacks=[progress_cb],
        show_progress_bar=False,
    )

    best_params = study.best_params
    print(f"\n搜索完成！最优 F1: {study.best_value:.4f}")
    print("最优参数：")
    for k, v in best_params.items():
        print(f"  {k}: {v}")

    # ── 用最优参数重训完整模型 ────────────────────────────────
    print("\n以最优参数重训完整模型...")
    test_df = df.iloc[split:].copy()
    X_train = train_df[feature_cols].values
    y_train = train_df["label"].values
    X_test  = test_df[feature_cols].values
    y_test  = test_df["label"].values

    final_params = {**best_params, "class_weight": "balanced", "verbose": -1}

    # 尝试 GPU
    try:
        final_params["device"] = "gpu"
        final_model = lgb.LGBMClassifier(**final_params)
        final_model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            callbacks=[lgb.early_stopping(50, verbose=False),
                       lgb.log_evaluation(50)],
        )
        print("GPU 训练完成")
    except Exception:
        final_params.pop("device", None)
        final_model = lgb.LGBMClassifier(**final_params)
        final_model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            callbacks=[lgb.early_stopping(50, verbose=False),
                       lgb.log_evaluation(50)],
        )

    # 测试集 F1
    y_pred = final_model.predict(X_test)
    f1_final = f1_score(y_test, y_pred, labels=[1], average="macro", zero_division=0)
    print(f"\n最终测试集 F1（做多类）: {f1_final:.4f}")

    # 保存（覆盖原模型）
    model_path = MODEL_DIR / f"lgbm_forward{forward}.pkl"
    with open(model_path, "wb") as f:
        pickle.dump({
            "model":        final_model,
            "feature_cols": feature_cols,
            "forward":      forward,
            "best_params":  best_params,
            "best_f1":      study.best_value,
        }, f)
    print(f"优化后模型已保存：{model_path}")

    # 保存 study（方便后续分析）
    study_path = MODEL_DIR / f"optuna_study_fwd{forward}.pkl"
    with open(study_path, "wb") as f:
        pickle.dump(study, f)
    print(f"Optuna study 已保存：{study_path}")

    return final_model, best_params


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--forward", type=int, default=FORWARD_DAYS, help="预测未来几日")
    parser.add_argument("--trials",  type=int, default=50,           help="搜索次数")
    args = parser.parse_args()
    tune(forward=args.forward, n_trials=args.trials)
