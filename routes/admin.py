"""routes/admin.py — 管理员专属 API（模型配置、邮件日志、系统状态、回测）"""

import json
import os
import pickle
from datetime import datetime

from flask import Blueprint, jsonify, request

from routes._shared import (
    require_admin,
    ROOT, EMAIL_LOG_FILE, THRESHOLD_FILE,
    read_model_config, write_model_config,
)

admin_bp = Blueprint("admin", __name__)


# ── 模型配置 ───────────────────────────────────────────────────

@admin_bp.get("/api/model-config")
@require_admin
def api_get_model_config():
    config     = read_model_config()
    calibrated = {}
    if THRESHOLD_FILE.exists():
        try:
            calibrated = json.loads(THRESHOLD_FILE.read_text("utf-8"))
        except Exception:
            pass
    return jsonify({"config": config, "calibrated": calibrated})


@admin_bp.put("/api/model-config")
@require_admin
def api_put_model_config():
    data   = request.json or {}
    config = read_model_config()
    if "prob_threshold" in data:
        v = float(data["prob_threshold"])
        if not (0.30 <= v <= 0.95):
            return jsonify({"error": "概率门槛需在 0.30 ~ 0.95 之间"}), 400
        config["prob_threshold"] = round(v, 3)
    if "blacklist" in data:
        config["blacklist"] = [str(c).strip() for c in data["blacklist"] if str(c).strip()]
    if "threshold_overrides" in data:
        overrides = {}
        for k, v in data["threshold_overrides"].items():
            overrides[k] = float(v) if v is not None else None
        config["threshold_overrides"] = overrides
    if "stop_loss" in data:
        v = float(data["stop_loss"])
        if not (0.01 <= v <= 0.50):
            return jsonify({"error": "止损线需在 1% ~ 50% 之间"}), 400
        config["stop_loss"] = round(v, 3)
    if "take_profit" in data:
        v = float(data["take_profit"])
        if not (0.01 <= v <= 1.00):
            return jsonify({"error": "止盈线需在 1% ~ 100% 之间"}), 400
        config["take_profit"] = round(v, 3)
    if "sell_prob_threshold" in data:
        v = float(data["sell_prob_threshold"])
        if not (0.40 <= v <= 0.95):
            return jsonify({"error": "模型看空阈值需在 40% ~ 95% 之间"}), 400
        config["sell_prob_threshold"] = round(v, 3)
    write_model_config(config)
    return jsonify(config)


@admin_bp.get("/api/model-versions")
@require_admin
def api_list_model_versions():
    """列出所有已保存的模型版本文件，标记当前激活版本。"""
    from quant.models.trainer import MODEL_DIR, FORWARD_DAYS

    config       = read_model_config()
    active_file  = config.get("active_models", {}).get(str(FORWARD_DAYS))

    versions = []
    for f in sorted(MODEL_DIR.glob(f"lgbm_forward{FORWARD_DAYS}_*.pkl"), reverse=True):
        stat = f.stat()
        versions.append({
            "filename":  f.name,
            "size_kb":   round(stat.st_size / 1024, 1),
            "saved_at":  datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
            "is_active": f.name == active_file,
        })

    # 兼容旧式固定文件名（如果存在且不在上面列表里）
    legacy = MODEL_DIR / f"lgbm_forward{FORWARD_DAYS}.pkl"
    if legacy.exists() and not any(v["filename"] == legacy.name for v in versions):
        stat = legacy.stat()
        versions.append({
            "filename":  legacy.name,
            "size_kb":   round(stat.st_size / 1024, 1),
            "saved_at":  datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
            "is_active": (legacy.name == active_file) or (active_file is None),
            "is_legacy": True,
        })

    return jsonify({
        "versions": versions,
        "active":   active_file,
        "forward":  FORWARD_DAYS,
    })


@admin_bp.post("/api/model-versions/activate")
@require_admin
def api_activate_model_version():
    """将指定文件设为激活版本（写入 model_config.json）。"""
    from quant.models.trainer import MODEL_DIR, FORWARD_DAYS, _set_active_model

    filename = (request.json or {}).get("filename", "").strip()
    if not filename:
        return jsonify({"error": "缺少 filename"}), 400

    # 防止路径穿越
    if os.sep in filename or "/" in filename or ".." in filename:
        return jsonify({"error": "非法文件名"}), 400

    path = MODEL_DIR / filename
    if not path.exists():
        return jsonify({"error": f"文件不存在：{filename}"}), 404

    try:
        with open(path, "rb") as f:
            bundle = pickle.load(f)
        if "model" not in bundle:
            return jsonify({"error": "不是有效的模型文件"}), 400
    except Exception as e:
        return jsonify({"error": f"验证模型失败：{e}"}), 400

    _set_active_model(FORWARD_DAYS, filename)
    return jsonify({"ok": True, "active": filename})


@admin_bp.post("/api/model-config/recalibrate")
@require_admin
def api_recalibrate():
    try:
        from quant.signals.calibrator import calibrate
        lookback = int((request.json or {}).get("lookback", 20))
        lookback = max(5, min(lookback, 120))
        result   = calibrate(lookback)
        return jsonify({"ok": True, "thresholds": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── 邮件日志 ───────────────────────────────────────────────────

@admin_bp.get("/api/email-log")
@require_admin
def api_email_log():
    if not EMAIL_LOG_FILE.exists():
        return jsonify([])
    lines = [l for l in EMAIL_LOG_FILE.read_text("utf-8").split("\n") if l.strip()]
    logs  = []
    for l in lines:
        try:
            logs.append(json.loads(l))
        except Exception:
            pass
    return jsonify(list(reversed(logs[-100:])))


# ── 系统状态 ───────────────────────────────────────────────────

@admin_bp.get("/api/system-status")
@require_admin
def api_system_status():
    def file_stat(rel):
        p = ROOT / rel
        if p.exists():
            mtime = datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            return {"exists": True, "last_modified": mtime}
        return {"exists": False, "last_modified": None}

    return jsonify({
        "signals":    file_stat("quant/signals/candidates.json"),
        "thresholds": file_stat("quant/signals/thresholds.json"),
        "users":      file_stat("portfolios/users.json"),
        "email_log":  file_stat("logs/email_log.jsonl"),
        "models":     file_stat("quant/models"),
    })


# ── 回测结果 ───────────────────────────────────────────────────

@admin_bp.get("/api/backtest")
@require_admin
def api_backtest():
    dirs = [
        ROOT / "quant" / "backtest" / "results",
        ROOT / "backtest_results",
    ]
    for d in dirs:
        if d.exists():
            results = []
            for f in sorted(d.glob("*.json"))[:30]:
                try:
                    obj = json.loads(f.read_text("utf-8"))
                    if isinstance(obj, dict):
                        results.append(obj)
                    elif isinstance(obj, list):
                        results.extend(obj)
                except Exception:
                    pass
            if results:
                return jsonify(results)
    return jsonify([])
