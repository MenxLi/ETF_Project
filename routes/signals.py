"""routes/signals.py — 买入/卖出信号、价格告警、模拟盘 API"""

import json
import re
import threading
from datetime import datetime

from flask import Blueprint, jsonify, request

from routes._shared import (
    get_current_user, require_auth, require_admin,
    CANDIDATE_FILE, SELL_CANDIDATES_FILE, ALERTS_FILE, SIGNAL_HISTORY_DIR,
    personalize_signals,
)

signals_bp = Blueprint("signals", __name__)

# ── 信号生成任务状态（进程内单例）────────────────────────────────
_sig_job: dict = {
    "status":       "idle",
    "started_at":   None,
    "finished_at":  None,
    "signal_count": 0,
    "log":          [],
    "error":        None,
}
_sig_lock = threading.Lock()


# ── 告警文件 I/O ───────────────────────────────────────────────

def _read_alerts() -> list:
    if not ALERTS_FILE.exists():
        return []
    try:
        return json.loads(ALERTS_FILE.read_text("utf-8")).get("alerts", [])
    except Exception:
        return []


def _write_alerts(alerts: list):
    ALERTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    ALERTS_FILE.write_text(
        json.dumps({"alerts": alerts}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# ── 买入信号 ───────────────────────────────────────────────────

@signals_bp.get("/api/signals")
@require_auth
def api_signals():
    if not CANDIDATE_FILE.exists():
        return jsonify({"trade_date": None, "generated_at": None, "signals": [], "count": 0})
    data = json.loads(CANDIDATE_FILE.read_text("utf-8"))
    me   = get_current_user()
    data["signals"] = personalize_signals(data.get("signals", []), me["id"])
    data["count"]   = len(data["signals"])
    return jsonify(data)


@signals_bp.post("/api/run-signals")
@require_admin
def api_run_signals():
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
        import contextlib, io
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                from quant.signals.generator import generate_signals
                signals = generate_signals()
            log_lines = [l for l in buf.getvalue().splitlines() if l.strip()][-10:]
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


@signals_bp.get("/api/run-signals/status")
@require_auth
def api_run_signals_status():
    with _sig_lock:
        return jsonify(dict(_sig_job))


# ── 卖出信号 ───────────────────────────────────────────────────

@signals_bp.get("/api/sell-signals")
@require_auth
def api_sell_signals():
    if not SELL_CANDIDATES_FILE.exists():
        return jsonify({"trade_date": None, "generated_at": None, "signals": [], "count": 0})
    data    = json.loads(SELL_CANDIDATES_FILE.read_text("utf-8"))
    me      = get_current_user()
    signals = data.get("users", {}).get(me["id"], [])
    return jsonify({
        "trade_date":   data.get("trade_date"),
        "generated_at": data.get("generated_at"),
        "signals":      signals,
        "count":        len(signals),
    })


@signals_bp.post("/api/sell-signals/run")
@require_admin
def api_run_sell_signals():
    def _run():
        try:
            from quant.signals.sell_generator import generate_sell_signals
            generate_sell_signals()
        except Exception as e:
            print(f"[卖出信号] 生成失败：{e}")

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"ok": True})


# ── 价格告警 ───────────────────────────────────────────────────

@signals_bp.get("/api/alerts")
@require_auth
def api_get_alerts():
    me     = get_current_user()
    alerts = _read_alerts()
    if me.get("role") == "admin":
        user_alerts = alerts
    else:
        user_alerts = [a for a in alerts if a.get("user_id") == me["id"]]
    active = [a for a in user_alerts if not a.get("dismissed", False)]
    active.sort(key=lambda a: a.get("timestamp", ""), reverse=True)
    return jsonify({"alerts": active, "count": len(active)})


@signals_bp.post("/api/alerts/<alert_id>/dismiss")
@require_auth
def api_dismiss_alert(alert_id):
    me     = get_current_user()
    alerts = _read_alerts()
    found  = False
    for a in alerts:
        if a.get("id") == alert_id:
            if me.get("role") != "admin" and a.get("user_id") != me["id"]:
                return jsonify({"error": "无权限"}), 403
            a["dismissed"] = True
            found = True
            break
    if not found:
        return jsonify({"error": "告警不存在"}), 404
    _write_alerts(alerts)
    return jsonify({"ok": True})


@signals_bp.post("/api/alerts/dismiss-all")
@require_auth
def api_dismiss_all_alerts():
    me     = get_current_user()
    alerts = _read_alerts()
    for a in alerts:
        if me.get("role") == "admin" or a.get("user_id") == me["id"]:
            a["dismissed"] = True
    _write_alerts(alerts)
    return jsonify({"ok": True})


@signals_bp.post("/api/alerts/run")
@require_admin
def api_run_monitor():
    def _run():
        try:
            from quant.signals.price_monitor import run_monitor
            run_monitor()
        except Exception as e:
            print(f"[价格监控] 手动触发失败：{e}")

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"ok": True})


# ── 历史档案 ───────────────────────────────────────────────────

@signals_bp.get("/api/signal-history")
@require_auth
def api_signal_history_index():
    if not SIGNAL_HISTORY_DIR.exists():
        return jsonify([])
    dates = sorted(
        [f.stem for f in SIGNAL_HISTORY_DIR.glob("????-??-??.json")],
        reverse=True,
    )[:90]
    return jsonify(dates)


@signals_bp.get("/api/signal-history/etf/<code>")
@require_auth
def api_signal_history_etf(code):
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


@signals_bp.get("/api/signal-history/<date>")
@require_auth
def api_signal_history_date(date):
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
        return jsonify({"error": "日期格式错误"}), 400
    hist_file = SIGNAL_HISTORY_DIR / f"{date}.json"
    if not hist_file.exists():
        return jsonify({"error": "该日期暂无记录"}), 404
    data    = json.loads(hist_file.read_text("utf-8"))
    me      = get_current_user()
    signals = personalize_signals(data.get("signals", []), me["id"])
    data["signals"] = signals
    data["count"]   = len(signals)
    return jsonify(data)


# ── 模拟盘 ─────────────────────────────────────────────────────

@signals_bp.get("/api/paper-trades")
@require_auth
def api_paper_trades():
    from quant.signals.paper_trader import load_paper_trades
    return jsonify(load_paper_trades())


@signals_bp.post("/api/paper-trades/refresh")
@require_admin
def api_paper_trades_refresh():
    try:
        from quant.signals.paper_trader import evaluate_all, load_paper_trades
        days = int((request.json or {}).get("days", 0)) or None
        evaluate_all(days)
        return jsonify(load_paper_trades())
    except Exception as e:
        return jsonify({"error": str(e)}), 500
