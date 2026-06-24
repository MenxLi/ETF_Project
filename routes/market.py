"""routes/market.py — 行情相关 API（实时价、ETF 列表、历史 K 线）"""

from flask import Blueprint, jsonify

from routes._shared import require_auth

market_bp = Blueprint("market", __name__)


def _sina_code(code: str) -> str:
    return ("sh" if (code.startswith("5") and not code.startswith("159")) else "sz") + code


@market_bp.get("/api/realtime-price/<code>")
@require_auth
def api_realtime_price(code):
    import urllib.request
    from quant.utils.etf_list import CODE_TO_NAME

    sina_code = _sina_code(code)
    try:
        url = f"https://hq.sinajs.cn/list={sina_code}"
        req = urllib.request.Request(url, headers={
            "Referer":    "https://finance.sina.com.cn",
            "User-Agent": "Mozilla/5.0",
        })
        with urllib.request.urlopen(req, timeout=4) as resp:
            text = resp.read().decode("gbk", errors="replace")

        inner = text.split('"')[1] if '"' in text else ""
        parts = inner.split(",")
        if len(parts) >= 10 and parts[3]:
            current    = float(parts[3])
            open_p     = float(parts[1]) if parts[1] else current
            prev_close = float(parts[2]) if parts[2] else current
            pct_chg    = round((current - prev_close) / prev_close * 100, 2) if prev_close else 0
            trade_time = parts[31] if len(parts) > 31 else ""
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
        pass

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


@market_bp.get("/api/etf-list")
@require_auth
def api_etf_list():
    from quant.utils.etf_list import CODE_TO_NAME, ETF_CATEGORIES
    return jsonify({"names": CODE_TO_NAME, "categories": ETF_CATEGORIES})


@market_bp.get("/api/etf-history/<code>")
@require_auth
def api_etf_history(code):
    try:
        from quant.data.fetch_historical import load
        df = load(code)
        if df is None or df.empty:
            return jsonify([])
        df      = df.tail(365).reset_index()
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
