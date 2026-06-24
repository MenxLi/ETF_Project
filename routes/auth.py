"""routes/auth.py — 认证相关 API"""

from flask import Blueprint, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from routes._shared import (
    get_current_user, read_users_raw, write_users,
    require_auth, require_admin,
)

auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/api/auth/login")
def api_login():
    data     = request.json or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    users    = read_users_raw()
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


@auth_bp.post("/api/auth/logout")
def api_logout():
    session.clear()
    return "", 204


@auth_bp.get("/api/auth/me")
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


@auth_bp.post("/api/auth/change-password")
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


@auth_bp.post("/api/users/<user_id>/reset-password")
@require_admin
def api_reset_password(user_id):
    data   = request.json or {}
    new_pw = data.get("password") or user_id
    users  = read_users_raw()
    u      = next((x for x in users if x["id"] == user_id), None)
    if not u:
        return jsonify({"error": "not found"}), 404
    u["password_hash"] = generate_password_hash(new_pw)
    write_users(users)
    return jsonify({"ok": True})
