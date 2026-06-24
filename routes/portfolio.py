"""routes/portfolio.py — 用户管理、持仓、交易记录 API"""

import re
from datetime import datetime

from flask import Blueprint, jsonify, request
from werkzeug.security import generate_password_hash

from routes._shared import (
    get_current_user, require_auth, require_admin,
    read_users_raw, read_users, write_users, _safe_user,
    read_portfolio, write_portfolio,
    read_transactions, write_transactions,
    _check_portfolio_access,
)

portfolio_bp = Blueprint("portfolio", __name__)


# ── 用户管理 ───────────────────────────────────────────────────

@portfolio_bp.get("/api/users")
@require_auth
def api_get_users():
    me    = get_current_user()
    users = read_users()
    if me.get("role") != "admin":
        users = [u for u in users if u["id"] == me["id"]]
    return jsonify([_safe_user(u) for u in users])


@portfolio_bp.post("/api/users")
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
        "password_hash":  generate_password_hash("gaoqian"),
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


@portfolio_bp.put("/api/users/<user_id>")
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


@portfolio_bp.delete("/api/users/<user_id>")
@require_admin
def api_delete_user(user_id):
    from routes._shared import _portfolio_path
    users = read_users_raw()
    user  = next((u for u in users if u["id"] == user_id), None)
    if not user:
        return jsonify({"error": "not found"}), 404
    p = _portfolio_path(user)
    if p.exists():
        p.unlink()
    write_users([u for u in users if u["id"] != user_id])
    return "", 204


# ── 自选列表 ───────────────────────────────────────────────────

@portfolio_bp.get("/api/watchlist")
@require_auth
def api_get_watchlist():
    me   = get_current_user()
    user = next((u for u in read_users_raw() if u["id"] == me["id"]), None)
    if not user:
        return jsonify([])
    pf = read_portfolio(user)
    return jsonify(pf.get("watchlist", []))


@portfolio_bp.put("/api/watchlist")
@require_auth
def api_put_watchlist():
    me   = get_current_user()
    user = next((u for u in read_users_raw() if u["id"] == me["id"]), None)
    if not user:
        return jsonify({"error": "user not found"}), 404
    codes = request.json if isinstance(request.json, list) else []
    pf = read_portfolio(user)
    pf["watchlist"] = codes
    write_portfolio(user, pf)
    return jsonify(codes)


# ── 持仓 ───────────────────────────────────────────────────────

@portfolio_bp.get("/api/portfolio/<user_id>")
@require_auth
def api_get_portfolio(user_id):
    user, err = _check_portfolio_access(user_id)
    if err:
        return err
    return jsonify(read_portfolio(user))


@portfolio_bp.put("/api/portfolio/<user_id>")
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


@portfolio_bp.post("/api/portfolio/<user_id>/positions")
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
    amount = round(new_pos["shares"] * new_pos["cost_price"], 2)
    if pos:
        old_shares = float(pos["shares"])
        old_cost   = float(pos["cost_price"])
        new_shares = old_shares + new_pos["shares"]
        new_cost   = round(
            (old_shares * old_cost + amount) / new_shares, 4
        ) if new_shares else old_cost
        new_pos["shares"]     = new_shares
        new_pos["cost_price"] = new_cost
        pos.update(new_pos)
    else:
        pf["positions"].append(new_pos)
    pf["cash"] = round(pf.get("cash", 0) - amount, 2)
    write_portfolio(user, pf)
    return jsonify(new_pos)


@portfolio_bp.delete("/api/portfolio/<user_id>/positions/<code>")
@require_auth
def api_delete_position(user_id, code):
    user, err = _check_portfolio_access(user_id)
    if err:
        return err
    pf = read_portfolio(user)
    pf["positions"] = [p for p in pf["positions"] if p["code"] != code]
    write_portfolio(user, pf)
    return "", 204


# ── 交易记录 ───────────────────────────────────────────────────

@portfolio_bp.get("/api/transactions/<user_id>")
@require_auth
def api_get_transactions(user_id):
    user, err = _check_portfolio_access(user_id)
    if err:
        return err
    return jsonify(list(reversed(read_transactions(user))))


@portfolio_bp.post("/api/transactions/<user_id>")
@require_auth
def api_create_transaction(user_id):
    user, err = _check_portfolio_access(user_id)
    if err:
        return err
    data   = request.json or {}
    action = data.get("action", "buy")
    code   = data.get("etf_code", "").strip()
    name   = data.get("etf_name", code)
    shares = float(data.get("shares", 0))
    price  = float(data.get("price",  0))
    amount = round(shares * price, 2)

    tx = {
        "id":         f"tx_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:20]}",
        "date":       data.get("date", datetime.now().strftime("%Y-%m-%d")),
        "action":     action,
        "etf_code":   code,
        "etf_name":   name,
        "shares":     shares,
        "price":      price,
        "amount":     amount,
        "note":       data.get("note", ""),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    txs = read_transactions(user)
    txs.append(tx)
    write_transactions(user, txs)

    pf  = read_portfolio(user)
    pos = next((p for p in pf["positions"] if p["code"] == code), None)

    if action == "buy":
        pf["cash"] = round(pf.get("cash", 0) - amount, 2)
        if pos:
            old_shares = float(pos["shares"])
            old_cost   = float(pos["cost_price"])
            new_shares = old_shares + shares
            new_cost   = round(
                (old_shares * old_cost + amount) / new_shares, 4
            ) if new_shares else old_cost
            pos["shares"]     = new_shares
            pos["cost_price"] = new_cost
        else:
            pf["positions"].append({
                "code":       code,
                "name":       name,
                "shares":     shares,
                "cost_price": round(price, 4),
                "buy_date":   data.get("date", datetime.now().strftime("%Y-%m-%d")),
            })
    elif action == "sell":
        pf["cash"] = round(pf.get("cash", 0) + amount, 2)
        if pos:
            remaining = float(pos["shares"]) - shares
            if remaining <= 0:
                pf["positions"] = [p for p in pf["positions"] if p["code"] != code]
            else:
                pos["shares"] = remaining

    write_portfolio(user, pf)
    return jsonify(tx), 201


@portfolio_bp.delete("/api/transactions/<user_id>/<tx_id>")
@require_auth
def api_delete_transaction(user_id, tx_id):
    user, err = _check_portfolio_access(user_id)
    if err:
        return err
    txs          = read_transactions(user)
    original_len = len(txs)
    txs          = [t for t in txs if t["id"] != tx_id]
    if len(txs) == original_len:
        return jsonify({"error": "not found"}), 404
    write_transactions(user, txs)
    return "", 204
