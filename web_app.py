"""
web_app.py  -  ETF 量化持仓管理界面 (Vue 3 版)
================================================
启动：
  cd D:\\AI_PROJECT
  .venv\\Scripts\\python.exe web_app.py

本地访问：  http://localhost:8888
外网访问：  ngrok http 8888  → 复制 https 链接

权限：
  管理员 (suiy)  — 可查看所有用户，回测/邮件/系统页
  普通用户        — 只可看自己的持仓和信号
"""

import json
import os
import re
import sys
import threading
from datetime import datetime
from functools import wraps
from pathlib import Path

from flask import Flask, Response, jsonify, request, session, send_from_directory
from werkzeug.security import check_password_hash, generate_password_hash

# ── 信号生成任务状态（全局单例）────────────────────────────────
_sig_job: dict = {
    "status":      "idle",   # idle | running | done | error
    "started_at":  None,
    "finished_at": None,
    "signal_count": 0,
    "log":         [],       # 最近几条进度日志
    "error":       None,
}
_sig_lock = threading.Lock()

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

USERS_FILE        = ROOT / "portfolios" / "users.json"
CANDIDATE_FILE    = ROOT / "quant" / "signals" / "candidates.json"
EMAIL_LOG_FILE    = ROOT / "logs" / "email_log.jsonl"
DIST_DIR          = ROOT / "static" / "dist"
SK_FILE           = ROOT / ".flask_secret"
MODEL_CONFIG_FILE = ROOT / "quant" / "signals" / "model_config.json"
THRESHOLD_FILE    = ROOT / "quant" / "signals" / "thresholds.json"
SIGNAL_HISTORY_DIR = ROOT / "quant" / "signals" / "history"

_CONFIG_DEFAULTS = {
    "prob_threshold": 0.50,
    "blacklist":      ["159869", "159766", "159928"],
    "threshold_overrides": {},
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

app = Flask(__name__)


# ── Secret key ─────────────────────────────────────────────────

if SK_FILE.exists():
    app.secret_key = SK_FILE.read_bytes()
else:
    _key = os.urandom(32)
    SK_FILE.write_bytes(_key)
    app.secret_key = _key

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=False,   # HTTP for local dev
    PERMANENT_SESSION_LIFETIME=86400 * 30,  # 30 days
)


# ── Config helpers ─────────────────────────────────────────────

def _web_password():
    try:
        from config import WEB_PASSWORD
        return WEB_PASSWORD
    except (ImportError, AttributeError):
        return "admin123"


# ── User data helpers ──────────────────────────────────────────

def read_users_raw():
    """Read ALL users including inactive."""
    if not USERS_FILE.exists():
        return []
    return json.loads(USERS_FILE.read_text("utf-8"))


def read_users():
    """Read active users only."""
    return [u for u in read_users_raw() if u.get("active", True)]


def write_users(users):
    USERS_FILE.write_text(
        json.dumps(users, ensure_ascii=False, indent=2), "utf-8"
    )


def _portfolio_path(user):
    return ROOT / user["portfolio_file"]


def read_portfolio(user):
    p = _portfolio_path(user)
    if not p.exists():
        return {"cash": 100000, "max_position_pct": 0.30,
                "max_sector_pct": 0.50, "positions": [], "updated_at": ""}
    return json.loads(p.read_text("utf-8"))


def write_portfolio(user, data):
    p = _portfolio_path(user)
    p.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")


def _safe_user(u):
    """Strip password_hash before returning to client."""
    return {k: v for k, v in u.items() if k != "password_hash"}


def _transactions_path(user):
    return ROOT / "portfolios" / f"{user['id']}_transactions.json"


def read_transactions(user):
    p = _transactions_path(user)
    if not p.exists():
        return []
    return json.loads(p.read_text("utf-8"))


def write_transactions(user, txs):
    p = _transactions_path(user)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(txs, ensure_ascii=False, indent=2), "utf-8")


# ── Migration ──────────────────────────────────────────────────

def _migrate_users():
    """Add role and password_hash fields to users.json if missing."""
    if not USERS_FILE.exists():
        return
    users   = read_users_raw()
    changed = False
    for u in users:
        if "role" not in u:
            u["role"] = "admin" if u.get("id") == "suiy" else "user"
            changed = True
        if "password_hash" not in u:
            default_pw = (
                _web_password() if u.get("role") == "admin"
                else "gaoqian"
            )
            u["password_hash"] = generate_password_hash(default_pw)
            changed = True
    if changed:
        write_users(users)
        print("  [迁移] users.json 已更新（添加 role / password_hash）")
        print("  [迁移] 普通用户的初始密码 = 用户 ID（登录后请修改）")


# ── Auth helpers ───────────────────────────────────────────────

def get_current_user():
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


# ── Auth API ───────────────────────────────────────────────────

@app.route("/api/auth/login", methods=["POST"])
def api_login():
    data     = request.json or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    users    = read_users_raw()
    # Match by id or display name
    user = next(
        (u for u in users
         if (u["id"] == username or u["name"] == username) and u.get("active", True)),
        None,
    )
    if not user or not check_password_hash(user.get("password_hash", ""), password):
        return jsonify({"error": "用户名或密码错误"}), 401
    session.permanent = True
    session["user_id"] = user["id"]
    return jsonify({
        "id":    user["id"],
        "name":  user["name"],
        "role":  user.get("role", "user"),
        "email": user.get("email", ""),
    })


@app.route("/api/auth/logout", methods=["POST"])
def api_logout():
    session.clear()
    return "", 204


@app.route("/api/auth/me")
def api_me():
    u = get_current_user()
    if not u:
        return jsonify({"error": "未登录"}), 401
    return jsonify({
        "id":    u["id"],
        "name":  u["name"],
        "role":  u.get("role", "user"),
        "email": u.get("email", ""),
    })


@app.route("/api/auth/change-password", methods=["POST"])
@require_auth
def api_change_password():
    data   = request.json or {}
    old_pw = data.get("old_password", "")
    new_pw = data.get("new_password", "")
    if not new_pw or len(new_pw) < 4:
        return jsonify({"error": "新密码至少 4 位"}), 400
    me    = get_current_user()
    users = read_users_raw()
    u     = next((x for x in users if x["id"] == me["id"]), None)
    if not check_password_hash(u.get("password_hash", ""), old_pw):
        return jsonify({"error": "原密码错误"}), 400
    u["password_hash"] = generate_password_hash(new_pw)
    write_users(users)
    return jsonify({"ok": True})


@app.route("/api/users/<user_id>/reset-password", methods=["POST"])
@require_admin
def api_reset_password(user_id):
    data   = request.json or {}
    new_pw = data.get("password") or user_id   # default = user id
    users  = read_users_raw()
    u      = next((x for x in users if x["id"] == user_id), None)
    if not u:
        return jsonify({"error": "not found"}), 404
    u["password_hash"] = generate_password_hash(new_pw)
    write_users(users)
    return jsonify({"ok": True})


# ── API: Realtime price ───────────────────────────────────────

def _sina_code(code: str) -> str:
    """将 ETF 代码转换为新浪财经格式，如 510300 → sh510300"""
    return ("sh" if (code.startswith("5") and not code.startswith("159")) else "sz") + code


@app.route("/api/realtime-price/<code>")
@require_auth
def api_realtime_price(code):
    """
    通过新浪财经接口获取单只 ETF 实时行情。
    交易时段返回实时最新价；非交易时段返回本地最后收盘价。
    """
    import urllib.request
    from datetime import time as dtime
    from quant.utils.etf_list import CODE_TO_NAME

    # 尝试拉取新浪实时行情
    sina_code = _sina_code(code)
    try:
        url = f"https://hq.sinajs.cn/list={sina_code}"
        req = urllib.request.Request(url, headers={
            "Referer": "https://finance.sina.com.cn",
            "User-Agent": "Mozilla/5.0",
        })
        with urllib.request.urlopen(req, timeout=4) as resp:
            text = resp.read().decode("gbk", errors="replace")

        # 解析：var hq_str_sh510300="name,open,prev_close,current,high,low,...,date,time"
        inner = text.split('"')[1] if '"' in text else ""
        parts = inner.split(",")
        if len(parts) >= 10 and parts[3]:
            current    = float(parts[3])
            open_p     = float(parts[1]) if parts[1] else current
            prev_close = float(parts[2]) if parts[2] else current
            pct_chg    = round((current - prev_close) / prev_close * 100, 2) if prev_close else 0
            trade_time = parts[31] if len(parts) > 31 else ""
            is_trading = bool(current and current != prev_close or trade_time >= "09:25")
            return jsonify({
                "code":       code,
                "name":       CODE_TO_NAME.get(code, code),
                "price":      round(current, 4),
                "open":       round(open_p, 4),
                "prev_close": round(prev_close, 4),
                "pct_chg":    pct_chg,
                "trade_time": trade_time,
                "source":     "realtime",
            })
    except Exception:
        pass  # 拉取失败，降级到本地收盘价

    # 降级：返回本地最后收盘价
    try:
        from quant.data.fetch_historical import load
        df = load(code)
        if df is not None and not df.empty:
            last = df.iloc[-1]
            return jsonify({
                "code":       code,
                "name":       CODE_TO_NAME.get(code, code),
                "price":      round(float(last["close"]), 4),
                "open":       round(float(last.get("open", last["close"])), 4),
                "prev_close": round(float(last["close"]), 4),
                "pct_chg":    0.0,
                "trade_time": str(last.get("date", ""))[:10],
                "source":     "local_close",
            })
    except Exception:
        pass

    return jsonify({"error": "无法获取行情"}), 404


# ── API: ETF list ─────────────────────────────────────────────

@app.route("/api/etf-list")
@require_auth
def api_etf_list():
    from quant.utils.etf_list import CODE_TO_NAME
    return jsonify(CODE_TO_NAME)


# ── API: Users ────────────────────────────────────────────────

@app.route("/api/users", methods=["GET"])
@require_auth
def api_get_users():
    me    = get_current_user()
    users = read_users()
    if me.get("role") != "admin":
        users = [u for u in users if u["id"] == me["id"]]
    return jsonify([_safe_user(u) for u in users])


@app.route("/api/users", methods=["POST"])
@require_admin
def api_create_user():
    data  = request.json
    users = read_users_raw()

    base_id  = re.sub(r"[^a-z0-9_]", "", data.get("name", "user").lower()) or "user"
    user_id  = base_id
    existing = {u["id"] for u in users}
    i = 1
    while user_id in existing:
        user_id = f"{base_id}_{i}"; i += 1

    new_user = {
        "id":             user_id,
        "name":           data.get("name", "新用户"),
        "email":          data.get("email", ""),
        "portfolio_file": f"portfolios/{user_id}.json",
        "active":         bool(data.get("active", True)),
        "role":           "user",
        "password_hash":  generate_password_hash("gaoqian"),  # 默认密码 = gaoqian
    }
    users.append(new_user)
    write_users(users)
    write_portfolio(new_user, {
        "cash":             float(data.get("cash", 100000)),
        "max_position_pct": float(data.get("max_position_pct", 0.30)),
        "max_sector_pct":   float(data.get("max_sector_pct", 0.50)),
        "positions":        [],
    })
    return jsonify(_safe_user(new_user)), 201


@app.route("/api/users/<user_id>", methods=["PUT"])
@require_auth
def api_update_user(user_id):
    me = get_current_user()
    if me.get("role") != "admin" and me["id"] != user_id:
        return jsonify({"error": "forbidden"}), 403
    data  = request.json
    users = read_users_raw()
    user  = next((u for u in users if u["id"] == user_id), None)
    if not user:
        return jsonify({"error": "not found"}), 404
    for k in ("name", "email", "active"):
        if k in data:
            user[k] = data[k]
    write_users(users)
    return jsonify(_safe_user(user))


@app.route("/api/users/<user_id>", methods=["DELETE"])
@require_admin
def api_delete_user(user_id):
    users = read_users_raw()
    user  = next((u for u in users if u["id"] == user_id), None)
    if not user:
        return jsonify({"error": "not found"}), 404
    p = _portfolio_path(user)
    if p.exists():
        p.unlink()
    write_users([u for u in users if u["id"] != user_id])
    return "", 204


# ── API: Portfolio ────────────────────────────────────────────

def _check_portfolio_access(user_id):
    """Return (user_dict, error_tuple). error_tuple is None if access ok."""
    me    = get_current_user()
    users = read_users()
    user  = next((u for u in users if u["id"] == user_id), None)
    if not user:
        return None, (jsonify({"error": "not found"}), 404)
    if me.get("role") != "admin" and me["id"] != user_id:
        return None, (jsonify({"error": "forbidden"}), 403)
    return user, None


@app.route("/api/watchlist", methods=["GET"])
@require_auth
def api_get_watchlist():
    """返回当前用户的自选 ETF 列表。"""
    me   = get_current_user()
    user = next((u for u in read_users_raw() if u["id"] == me["id"]), None)
    if not user:
        return jsonify([])
    pf = read_portfolio(user)
    return jsonify(pf.get("watchlist", []))


@app.route("/api/watchlist", methods=["PUT"])
@require_auth
def api_put_watchlist():
    """保存当前用户的自选 ETF 列表。"""
    me   = get_current_user()
    user = next((u for u in read_users_raw() if u["id"] == me["id"]), None)
    if not user:
        return jsonify({"error": "user not found"}), 404
    codes = request.json if isinstance(request.json, list) else []
    pf = read_portfolio(user)
    pf["watchlist"] = codes
    write_portfolio(user, pf)
    return jsonify(codes)


@app.route("/api/portfolio/<user_id>", methods=["GET"])
@require_auth
def api_get_portfolio(user_id):
    user, err = _check_portfolio_access(user_id)
    if err:
        return err
    return jsonify(read_portfolio(user))


@app.route("/api/portfolio/<user_id>", methods=["PUT"])
@require_auth
def api_update_portfolio(user_id):
    user, err = _check_portfolio_access(user_id)
    if err:
        return err
    data = request.json
    pf   = read_portfolio(user)
    pf["cash"]             = float(data.get("cash",             pf["cash"]))
    pf["max_position_pct"] = float(data.get("max_position_pct", pf["max_position_pct"]))
    pf["max_sector_pct"]   = float(data.get("max_sector_pct",   pf["max_sector_pct"]))
    write_portfolio(user, pf)
    return jsonify(pf)


@app.route("/api/portfolio/<user_id>/positions", methods=["POST"])
@require_auth
def api_upsert_position(user_id):
    user, err = _check_portfolio_access(user_id)
    if err:
        return err
    data = request.json
    code = data["code"]
    pf   = read_portfolio(user)
    pos  = next((p for p in pf["positions"] if p["code"] == code), None)
    new_pos = {
        "code":       code,
        "name":       data.get("name", code),
        "shares":     float(data.get("shares", 0)),
        "cost_price": float(data.get("cost_price", 0)),
        "buy_date":   data.get("buy_date", datetime.now().strftime("%Y-%m-%d")),
    }
    if pos:
        pos.update(new_pos)
    else:
        pf["positions"].append(new_pos)
    write_portfolio(user, pf)
    return jsonify(new_pos)


@app.route("/api/portfolio/<user_id>/positions/<code>", methods=["DELETE"])
@require_auth
def api_delete_position(user_id, code):
    user, err = _check_portfolio_access(user_id)
    if err:
        return err
    pf = read_portfolio(user)
    pf["positions"] = [p for p in pf["positions"] if p["code"] != code]
    write_portfolio(user, pf)
    return "", 204


# ── API: Transactions ─────────────────────────────────────────

@app.route("/api/transactions/<user_id>", methods=["GET"])
@require_auth
def api_get_transactions(user_id):
    user, err = _check_portfolio_access(user_id)
    if err:
        return err
    txs = read_transactions(user)
    # Newest first
    return jsonify(list(reversed(txs)))


@app.route("/api/transactions/<user_id>", methods=["POST"])
@require_auth
def api_create_transaction(user_id):
    user, err = _check_portfolio_access(user_id)
    if err:
        return err
    data  = request.json or {}
    shares = float(data.get("shares", 0))
    price  = float(data.get("price",  0))
    tx = {
        "id":         f"tx_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:20]}",
        "date":       data.get("date", datetime.now().strftime("%Y-%m-%d")),
        "action":     data.get("action", "buy"),    # "buy" | "sell"
        "etf_code":   data.get("etf_code", ""),
        "etf_name":   data.get("etf_name", ""),
        "shares":     shares,
        "price":      price,
        "amount":     round(shares * price, 2),
        "note":       data.get("note", ""),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    txs = read_transactions(user)
    txs.append(tx)
    write_transactions(user, txs)
    return jsonify(tx), 201


@app.route("/api/transactions/<user_id>/<tx_id>", methods=["DELETE"])
@require_auth
def api_delete_transaction(user_id, tx_id):
    user, err = _check_portfolio_access(user_id)
    if err:
        return err
    txs = read_transactions(user)
    original_len = len(txs)
    txs = [t for t in txs if t["id"] != tx_id]
    if len(txs) == original_len:
        return jsonify({"error": "not found"}), 404
    write_transactions(user, txs)
    return "", 204


# ── API: Signals ──────────────────────────────────────────────

@app.route("/api/signals")
@require_auth
def api_signals():
    if not CANDIDATE_FILE.exists():
        return jsonify({"trade_date": None, "generated_at": None, "signals": [], "count": 0})
    data = json.loads(CANDIDATE_FILE.read_text("utf-8"))

    me = get_current_user()
    data["signals"] = _personalize_signals(data.get("signals", []), me["id"])
    data["count"]   = len(data["signals"])
    return jsonify(data)


# ── API: Manual signal trigger ───────────────────────────────

@app.route("/api/run-signals", methods=["POST"])
@require_admin
def api_run_signals():
    """在后台线程启动信号生成，立即返回。"""
    with _sig_lock:
        if _sig_job["status"] == "running":
            return jsonify({"error": "信号生成正在进行中，请稍候"}), 409
        _sig_job.update({
            "status":       "running",
            "started_at":   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "finished_at":  None,
            "signal_count": 0,
            "log":          ["[开始] 正在更新行情数据，请稍候…"],
            "error":        None,
        })

    def _run():
        import io, contextlib
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                from quant.signals.generator import generate_signals
                signals = generate_signals()
            output = buf.getvalue()
            log_lines = [l for l in output.splitlines() if l.strip()][-10:]
            with _sig_lock:
                _sig_job.update({
                    "status":       "done",
                    "finished_at":  datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "signal_count": len(signals),
                    "log":          log_lines or ["[完成] 信号生成成功"],
                    "error":        None,
                })
        except Exception as e:
            with _sig_lock:
                _sig_job.update({
                    "status":      "error",
                    "finished_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "log":         ["[错误] " + str(e)],
                    "error":       str(e),
                })

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"ok": True})


@app.route("/api/run-signals/status")
@require_auth
def api_run_signals_status():
    """返回当前信号生成任务状态。"""
    with _sig_lock:
        return jsonify(dict(_sig_job))


# ── API: Email log ────────────────────────────────────────────

@app.route("/api/email-log")
@require_admin
def api_email_log():
    if not EMAIL_LOG_FILE.exists():
        return jsonify([])
    lines = [l for l in EMAIL_LOG_FILE.read_text("utf-8").split("\n") if l.strip()]
    logs = []
    for l in lines:
        try:
            logs.append(json.loads(l))
        except Exception:
            pass
    return jsonify(list(reversed(logs[-100:])))


# ── API: System status ────────────────────────────────────────

@app.route("/api/system-status")
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


# ── API: ETF history ──────────────────────────────────────────

@app.route("/api/etf-history/<code>")
@require_auth
def api_etf_history(code):
    try:
        from quant.data.fetch_historical import load
        df = load(code)
        if df is None or df.empty:
            return jsonify([])
        df = df.tail(365).reset_index()
        records = []
        for _, row in df.iterrows():
            date_val = row.get("date") or row.get("trade_date") or str(row.name)
            records.append({
                "date":   str(date_val)[:10],
                "close":  round(float(row.get("close",  0)), 4),
                "open":   round(float(row.get("open",   row.get("close", 0))), 4),
                "high":   round(float(row.get("high",   row.get("close", 0))), 4),
                "low":    round(float(row.get("low",    row.get("close", 0))), 4),
                "volume": float(row.get("volume", 0)),
            })
        return jsonify(records)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── API: Signal history ───────────────────────────────────────

def _personalize_signals(signals: list, user_id: str) -> list:
    """共用的个性化建议逻辑，用于今日信号和历史档案。"""
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
            advised, _ = advise_for_user(signals, u_model)
            return advised
    except Exception:
        pass
    return signals


@app.route("/api/signal-history")
@require_auth
def api_signal_history_index():
    """返回有历史记录的日期列表（最近 90 天，降序）。"""
    if not SIGNAL_HISTORY_DIR.exists():
        return jsonify([])
    dates = sorted(
        [f.stem for f in SIGNAL_HISTORY_DIR.glob("????-??-??.json")],
        reverse=True
    )[:90]
    return jsonify(dates)


@app.route("/api/signal-history/etf/<code>")
@require_auth
def api_signal_history_etf(code):
    """返回某只 ETF 在历史档案中出现过的所有信号日期及做多概率。"""
    if not SIGNAL_HISTORY_DIR.exists():
        return jsonify([])
    results = []
    for f in sorted(SIGNAL_HISTORY_DIR.glob("????-??-??.json")):
        try:
            data = json.loads(f.read_text("utf-8"))
            for sig in data.get("signals", []):
                if sig.get("code") == code:
                    results.append({
                        "date":    f.stem,
                        "prob_up": round(float(sig.get("prob_up", 0)), 4),
                        "close":   round(float(sig.get("close", 0)), 4),
                    })
                    break
        except Exception:
            pass
    return jsonify(results)


@app.route("/api/signal-history/<date>")
@require_auth
def api_signal_history_date(date):
    """返回指定日期的信号，并叠加当前用户的个性化建议。"""
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
        return jsonify({"error": "日期格式错误"}), 400
    hist_file = SIGNAL_HISTORY_DIR / f"{date}.json"
    if not hist_file.exists():
        return jsonify({"error": "该日期暂无记录"}), 404
    data    = json.loads(hist_file.read_text("utf-8"))
    me      = get_current_user()
    signals = _personalize_signals(data.get("signals", []), me["id"])
    data["signals"] = signals
    data["count"]   = len(signals)
    return jsonify(data)


# ── API: Model config ────────────────────────────────────────

@app.route("/api/model-config", methods=["GET"])
@require_admin
def api_get_model_config():
    config = read_model_config()
    calibrated = {}
    if THRESHOLD_FILE.exists():
        try:
            calibrated = json.loads(THRESHOLD_FILE.read_text("utf-8"))
        except Exception:
            pass
    return jsonify({"config": config, "calibrated": calibrated})


@app.route("/api/model-config", methods=["PUT"])
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
    write_model_config(config)
    return jsonify(config)


@app.route("/api/model-config/recalibrate", methods=["POST"])
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


# ── API: Paper trades ────────────────────────────────────────

@app.route("/api/paper-trades")
@require_auth
def api_paper_trades():
    from quant.signals.paper_trader import load_paper_trades
    return jsonify(load_paper_trades())


@app.route("/api/paper-trades/refresh", methods=["POST"])
@require_admin
def api_paper_trades_refresh():
    try:
        from quant.signals.paper_trader import evaluate_all
        days = int((request.json or {}).get("days", 0)) or None
        evaluate_all(days)
        from quant.signals.paper_trader import load_paper_trades
        return jsonify(load_paper_trades())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── API: Backtest ─────────────────────────────────────────────

@app.route("/api/backtest")
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


# ── Frontend (SPA catch-all) ──────────────────────────────────
# NOTE: No @require_auth here — the Vue login page must be accessible.

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_spa(path):
    if not DIST_DIR.exists():
        return Response(
            "前端尚未构建，请在 frontend/ 目录执行 npm run build",
            503, {"Content-Type": "text/plain; charset=utf-8"},
        )
    target = DIST_DIR / path if path else DIST_DIR / "index.html"
    if path and target.exists() and target.is_file():
        return send_from_directory(DIST_DIR, path)
    return send_from_directory(DIST_DIR, "index.html")


# ── Main ──────────────────────────────────────────────────────

if __name__ == "__main__":
    import socket
    _migrate_users()
    try:
        local_ip = socket.gethostbyname(socket.gethostname())
    except Exception:
        local_ip = "127.0.0.1"
    print("=" * 50)
    print("  ETF 量化管理界面  (Vue 3 + 多用户认证)")
    print("=" * 50)
    print("  本地:   http://localhost:8888")
    print("  局域网: http://" + local_ip + ":8888")
    print("  管理员: suiy  /  密码:", _web_password())
    print("=" * 50)
    app.run(host="0.0.0.0", port=8888, debug=False)
