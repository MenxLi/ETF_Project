"""
routes/_shared.py
共享常量、文件 I/O 助手、认证装饰器。
所有 Blueprint 从这里 import，不直接访问文件系统路径。
"""

import json
import sys
from datetime import datetime
from functools import wraps
from pathlib import Path

from flask import jsonify, session
from werkzeug.security import generate_password_hash

# ── 路径常量 ───────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

USERS_FILE           = ROOT / "portfolios" / "users.json"
CANDIDATE_FILE       = ROOT / "quant" / "signals" / "candidates.json"
SELL_CANDIDATES_FILE = ROOT / "quant" / "signals" / "sell_candidates.json"
ALERTS_FILE          = ROOT / "quant" / "signals" / "alerts.json"
EMAIL_LOG_FILE       = ROOT / "logs" / "email_log.jsonl"
MODEL_CONFIG_FILE    = ROOT / "quant" / "signals" / "model_config.json"
THRESHOLD_FILE       = ROOT / "quant" / "signals" / "thresholds.json"
SIGNAL_HISTORY_DIR   = ROOT / "quant" / "signals" / "history"
DIST_DIR             = ROOT / "static" / "dist"

# ── 模型配置 ───────────────────────────────────────────────────
_CONFIG_DEFAULTS: dict = {
    "prob_threshold":     0.50,
    "blacklist":          ["159869", "159766", "159928"],
    "threshold_overrides": {},
    "stop_loss":          0.05,
    "take_profit":        0.08,
    "sell_prob_threshold": 0.55,
    "active_models":      {},   # { "5": "lgbm_forward5_20260624.pkl" }
}


def read_model_config() -> dict:
    if MODEL_CONFIG_FILE.exists():
        try:
            saved = json.loads(MODEL_CONFIG_FILE.read_text("utf-8"))
            return {**_CONFIG_DEFAULTS, **saved}
        except Exception:
            pass
    return _CONFIG_DEFAULTS.copy()


def write_model_config(data: dict):
    MODEL_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    MODEL_CONFIG_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")


# ── 用户 I/O ───────────────────────────────────────────────────

def read_users_raw() -> list:
    if not USERS_FILE.exists():
        return []
    return json.loads(USERS_FILE.read_text("utf-8"))


def read_users() -> list:
    return [u for u in read_users_raw() if u.get("active", True)]


def write_users(users: list):
    USERS_FILE.write_text(json.dumps(users, ensure_ascii=False, indent=2), "utf-8")


def _safe_user(u: dict) -> dict:
    return {k: v for k, v in u.items() if k != "password_hash"}


# ── 持仓 / 交易 I/O ────────────────────────────────────────────

def _portfolio_path(user: dict) -> Path:
    return ROOT / user["portfolio_file"]


def read_portfolio(user: dict) -> dict:
    p = _portfolio_path(user)
    if not p.exists():
        return {
            "cash": 100000, "max_position_pct": 0.30,
            "max_sector_pct": 0.50, "positions": [], "updated_at": "",
        }
    return json.loads(p.read_text("utf-8"))


def write_portfolio(user: dict, data: dict):
    p = _portfolio_path(user)
    p.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")


def _transactions_path(user: dict) -> Path:
    return ROOT / "portfolios" / f"{user['id']}_transactions.json"


def read_transactions(user: dict) -> list:
    p = _transactions_path(user)
    if not p.exists():
        return []
    return json.loads(p.read_text("utf-8"))


def write_transactions(user: dict, txs: list):
    p = _transactions_path(user)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(txs, ensure_ascii=False, indent=2), "utf-8")


def _check_portfolio_access(user_id: str):
    """Return (user_dict, error_tuple). error_tuple is None if access ok."""
    me    = get_current_user()
    users = read_users()
    user  = next((u for u in users if u["id"] == user_id), None)
    if not user:
        return None, (jsonify({"error": "not found"}), 404)
    if me.get("role") != "admin" and me["id"] != user_id:
        return None, (jsonify({"error": "forbidden"}), 403)
    return user, None


# ── 认证 ───────────────────────────────────────────────────────

def get_current_user() -> dict | None:
    user_id = session.get("user_id")
    if not user_id:
        return None
    return next((u for u in read_users_raw() if u["id"] == user_id), None)


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not get_current_user():
            return jsonify({"error": "请先登录"}), 401
        return f(*args, **kwargs)
    return decorated


def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        u = get_current_user()
        if not u or u.get("role") != "admin":
            return jsonify({"error": "需要管理员权限"}), 403
        return f(*args, **kwargs)
    return decorated


# ── 信号个性化 ─────────────────────────────────────────────────

def personalize_signals(signals: list, user_id: str) -> list:
    """叠加用户持仓视角的建议标签（仓位状态、浮盈亏等）。"""
    try:
        from quant.portfolio.manager import advise_for_user, User
        users    = read_users()
        user_obj = next((u for u in users if u["id"] == user_id), None)
        if user_obj:
            u_model = User(
                id=user_obj["id"], name=user_obj["name"],
                email=user_obj.get("email", ""),
                portfolio_file=user_obj["portfolio_file"],
                active=user_obj.get("active", True),
            )
            price_map = {s["code"]: float(s["close"])
                         for s in signals if s.get("close")}
            advised, _ = advise_for_user(signals, u_model, price_map)
            return advised
    except Exception:
        pass
    return signals
