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

import os
import sys
from pathlib import Path

from flask import Flask, Response, send_from_directory
from werkzeug.security import generate_password_hash

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

DIST_DIR = ROOT / "static" / "dist"
SK_FILE  = ROOT / ".flask_secret"

# ── App ────────────────────────────────────────────────────────
app = Flask(__name__)

if SK_FILE.exists():
    app.secret_key = SK_FILE.read_bytes()
else:
    _key = os.urandom(32)
    SK_FILE.write_bytes(_key)
    app.secret_key = _key

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=False,
    PERMANENT_SESSION_LIFETIME=86400 * 30,
)

# ── Blueprints ─────────────────────────────────────────────────
from routes.auth      import auth_bp
from routes.portfolio import portfolio_bp
from routes.signals   import signals_bp
from routes.admin     import admin_bp
from routes.market    import market_bp

for bp in (auth_bp, portfolio_bp, signals_bp, admin_bp, market_bp):
    app.register_blueprint(bp)


# ── Frontend (SPA catch-all) ──────────────────────────────────
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


# ── Startup helpers ────────────────────────────────────────────
def _web_password():
    try:
        from config import WEB_PASSWORD
        return WEB_PASSWORD
    except (ImportError, AttributeError):
        return "admin123"


def _migrate_users():
    from routes._shared import USERS_FILE, read_users_raw, write_users
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
                _web_password() if u.get("role") == "admin" else "gaoqian"
            )
            u["password_hash"] = generate_password_hash(default_pw)
            changed = True
    if changed:
        write_users(users)
        print("  [迁移] users.json 已更新（添加 role / password_hash）")


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
