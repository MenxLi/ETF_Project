"""
notifier.py
------------
格式化信号日报，通过 Gmail SMTP 发送 HTML 邮件。

配置：在 config.py 中填写
  SMTP_SENDER   = "your_gmail@gmail.com"
  SMTP_PASSWORD = "xxxx xxxx xxxx xxxx"   # Gmail App Password
"""

import json
import smtplib
import ssl
from datetime import date, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr
from pathlib import Path

_LOG_FILE = Path(__file__).parent.parent.parent / "logs" / "email_log.jsonl"


def _log_email(to, subject, success, error=None):
    """Append send record to logs/email_log.jsonl"""
    try:
        _LOG_FILE.parent.mkdir(exist_ok=True)
        entry = {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                 "to": to, "subject": subject, "success": success}
        if error:
            entry["error"] = str(error)
        with _LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


# ── SMTP 发送 ─────────────────────────────────────────────────

def _load_smtp_config():
    try:
        import config
        sender   = getattr(config, "SMTP_SENDER",   "")
        password = getattr(config, "SMTP_PASSWORD", "")
        if "@" in sender and password not in ("", "xxxx xxxx xxxx xxxx", "YOUR_163_AUTH_CODE"):
            return {
                "sender":   sender,
                "password": password,
                "host":     getattr(config, "SMTP_HOST", "smtp.gmail.com"),
                "port":     getattr(config, "SMTP_PORT", 465),
            }
    except ImportError:
        pass
    return None


def send_email(to, subject, html_body):
    """通过 Gmail SMTP SSL 发送 HTML 邮件，返回是否成功。"""
    cfg = _load_smtp_config()
    if not cfg:
        print("[邮件] 未配置 SMTP，请在 config.py 中填写 SMTP_SENDER / SMTP_PASSWORD")
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = formataddr((str(Header("ETF量化助手", "utf-8")), cfg["sender"]))
        msg["To"]      = to
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(cfg["host"], cfg["port"], context=ctx) as server:
            server.login(cfg["sender"], cfg["password"])
            server.sendmail(cfg["sender"], to, msg.as_string())

        print("[邮件] 已发送至 " + to)
        _log_email(to, subject, True)
        return True
    except Exception as e:
        print("[邮件] 发送失败 (" + to + "): " + str(e))
        _log_email(to, subject, False, e)
        return False


# ── 颜色常量 ──────────────────────────────────────────────────

ADVICE_EMOJI = {"OPEN": "🟢", "ADD": "🔵", "HOLD": "🟡", "REDUCE": "🔴", "SKIP": "⚫"}
ADVICE_COLOR = {
    "OPEN":   "#22c55e",
    "ADD":    "#3b82f6",
    "HOLD":   "#eab308",
    "REDUCE": "#ef4444",
    "SKIP":   "#6b7280",
}


# ── 日报 HTML ─────────────────────────────────────────────────

def _html_daily(signals, forward, portfolio=None, user_name=""):
    today    = date.today().strftime("%Y-%m-%d")
    n        = len(signals)
    greeting = ("你好 " + user_name + "，") if user_name else ""
    subject  = ("📊 ETF量化日报 " + today + " | "
                + (str(n) + "个做多信号" if n else "无信号·观望"))

    # 持仓概览
    portfolio_html = ""
    if portfolio is not None:
        pos_rows = ""
        for p in portfolio.positions:
            pnl_pct   = p.unrealized_pct
            pnl_str   = ("+" if pnl_pct >= 0 else "") + "{:.1%}".format(pnl_pct)
            pnl_color = "#22c55e" if pnl_pct >= 0 else "#ef4444"
            pos_rows += (
                "<tr>"
                "<td>" + p.name + "</td>"
                "<td style='text-align:center'>" + p.code + "</td>"
                "<td style='text-align:right'>" + "{:.2f}".format(p.cost_price) + "</td>"
                "<td style='text-align:right;color:" + pnl_color + ";font-weight:600'>"
                + pnl_str + "</td>"
                "</tr>"
            )
        pos_table = (
            "<table width='100%' cellpadding='6' cellspacing='0'"
            " style='border-collapse:collapse;font-size:13px;margin-top:8px'>"
            "<tr style='background:#f3f4f6;color:#6b7280;font-size:12px'>"
            "<th style='text-align:left'>标的</th>"
            "<th style='text-align:center'>代码</th>"
            "<th style='text-align:right'>成本价</th>"
            "<th style='text-align:right'>浮盈亏</th>"
            "</tr>"
            + (pos_rows if pos_rows else
               "<tr><td colspan='4' style='color:#9ca3af;text-align:center;"
               "padding:12px'>暂无持仓</td></tr>")
            + "</table>"
        )
        total_val = "{:,.0f}".format(portfolio.total_value)
        pos_pct   = "{:.1%}".format(portfolio.position_pct)
        cash_val  = "{:,.0f}".format(portfolio.cash)
        portfolio_html = (
            "<div style='background:#f0fdf4;border-left:4px solid #22c55e;"
            "padding:14px 16px;border-radius:6px;margin-bottom:20px'>"
            "<div style='font-size:13px;color:#374151;margin-bottom:8px'>"
            "<strong>💼 持仓概览</strong></div>"
            "<div style='font-size:13px'>"
            "总资产 <strong>" + total_val + "</strong> 元 &nbsp;"
            "仓位 <strong>" + pos_pct + "</strong> &nbsp;"
            "可用现金 <strong>" + cash_val + "</strong> 元"
            "</div>" + pos_table + "</div>"
        )

    # 信号列表
    if not signals:
        signals_html = (
            "<div style='text-align:center;padding:32px 0;color:#9ca3af'>"
            "<div style='font-size:36px'>⚪</div>"
            "<div style='margin-top:8px;font-size:15px'>今日无做多信号</div>"
            "<div style='margin-top:4px;font-size:13px'>"
            "模型未发现置信度足够的机会，建议持币观望</div></div>"
        )
    else:
        sig_rows = ""
        for s in signals:
            advice    = s.get("advice", "OPEN")
            emoji     = ADVICE_EMOJI.get(advice, "🟢")
            color     = ADVICE_COLOR.get(advice, "#22c55e")
            name      = s["name"]
            code      = s["code"]
            prob      = "{:.1%}".format(s["prob_up"])
            bar_w     = str(int(s["prob_up"] * 100))
            close_p   = "{:.2f}".format(s["close"])
            chg       = s["pct_chg"]
            chg_str   = ("+" if chg >= 0 else "") + "{:.2f}%".format(chg)
            chg_color = "#22c55e" if chg >= 0 else "#ef4444"
            reason    = s.get("advice_reason", "")
            sig_rows += (
                "<tr style='border-bottom:1px solid #f3f4f6'>"
                "<td style='padding:10px 8px'>"
                "<span style='background:" + color + "22;color:" + color + ";"
                "font-size:12px;font-weight:600;padding:2px 7px;border-radius:4px'>"
                + emoji + " " + advice + "</span></td>"
                "<td style='padding:10px 8px'>"
                "<div style='font-weight:600;font-size:14px'>" + name + "</div>"
                "<div style='color:#9ca3af;font-size:12px'>" + code + "</div></td>"
                "<td style='padding:10px 8px;text-align:center'>"
                "<div style='font-size:14px;font-weight:600'>" + prob + "</div>"
                "<div style='background:#e5e7eb;border-radius:4px;height:4px;"
                "width:60px;margin:4px auto 0'>"
                "<div style='background:" + color + ";height:4px;border-radius:4px;"
                "width:" + bar_w + "%'></div></div></td>"
                "<td style='padding:10px 8px;text-align:right'>"
                "<div style='font-size:14px'>" + close_p + "</div>"
                "<div style='color:" + chg_color + ";font-size:12px'>" + chg_str + "</div></td>"
                "<td style='padding:10px 8px;color:#6b7280;font-size:13px'>"
                + reason + "</td></tr>"
            )
        signals_html = (
            "<table width='100%' cellpadding='0' cellspacing='0'"
            " style='border-collapse:collapse;font-size:13px'>"
            "<tr style='background:#f9fafb;color:#6b7280;font-size:12px'>"
            "<th style='padding:8px;text-align:left'>建议</th>"
            "<th style='padding:8px;text-align:left'>标的</th>"
            "<th style='padding:8px;text-align:center'>做多概率</th>"
            "<th style='padding:8px;text-align:right'>现价</th>"
            "<th style='padding:8px;text-align:left'>操作说明</th>"
            "</tr>" + sig_rows + "</table>"
            "<p style='color:#9ca3af;font-size:12px;margin-top:16px'>"
            "持有约 " + str(forward) + " 个交易日后观察止盈/止损。</p>"
        )

    html = (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "</head><body style='margin:0;padding:0;background:#f3f4f6;"
        "font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif'>"
        "<div style='max-width:620px;margin:24px auto;background:#fff;"
        "border-radius:12px;overflow:hidden;box-shadow:0 1px 4px #0001'>"
        "<div style='background:linear-gradient(135deg,#1e40af,#3b82f6);"
        "padding:24px 28px;color:#fff'>"
        "<div style='font-size:20px;font-weight:700'>📊 ETF 量化日报</div>"
        "<div style='font-size:13px;margin-top:4px;opacity:.85'>"
        + today + " &nbsp;·&nbsp; 预测周期 " + str(forward) + " 个交易日</div></div>"
        "<div style='padding:24px 28px'>"
        "<p style='color:#374151;font-size:14px;margin:0 0 20px'>"
        + greeting + "以下是今日 ETF 量化信号与持仓建议。</p>"
        + portfolio_html
        + "<div style='font-size:15px;font-weight:600;color:#111827;margin-bottom:12px'>"
        "🟢 做多信号（" + str(n) + " 只）</div>"
        + signals_html
        + "</div>"
        "<div style='background:#f9fafb;padding:14px 28px;"
        "font-size:12px;color:#9ca3af;border-top:1px solid #f3f4f6'>"
        "本邮件由量化系统自动发送，仅供参考，不构成投资建议。</div>"
        "</div></body></html>"
    )
    return subject, html


# ── 盘中确认 HTML ─────────────────────────────────────────────

def _html_intraday(node_label, confirmed):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    n       = len(confirmed)
    subject = "📈 " + node_label + "信号确认 " + now_str + " | " + str(n) + "只"

    rows = ""
    for s in confirmed:
        rt        = s["rt"]
        name      = s["name"]
        code      = s["code"]
        prob      = "{:.1%}".format(s["prob_up"])
        price_str = "{:.2f}".format(rt["price"])
        chg       = rt["pct_chg"]
        chg_str   = ("+" if chg >= 0 else "") + "{:.2f}%".format(chg)
        chg_color = "#22c55e" if chg >= 0 else "#ef4444"
        reason    = s["reason"]
        rows += (
            "<tr style='border-bottom:1px solid #f3f4f6'>"
            "<td style='padding:10px 8px;font-weight:600'>" + name + "</td>"
            "<td style='padding:10px 8px;color:#6b7280'>" + code + "</td>"
            "<td style='padding:10px 8px;text-align:center'>" + prob + "</td>"
            "<td style='padding:10px 8px;text-align:right'>" + price_str + "</td>"
            "<td style='padding:10px 8px;text-align:right;color:" + chg_color
            + ";font-weight:600'>" + chg_str + "</td>"
            "<td style='padding:10px 8px;color:#6b7280;font-size:13px'>"
            + reason + "</td></tr>"
        )

    html = (
        "<!DOCTYPE html><html><head><meta charset='utf-8'></head>"
        "<body style='margin:0;padding:0;background:#f3f4f6;"
        "font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif'>"
        "<div style='max-width:620px;margin:24px auto;background:#fff;"
        "border-radius:12px;overflow:hidden;box-shadow:0 1px 4px #0001'>"
        "<div style='background:linear-gradient(135deg,#065f46,#10b981);"
        "padding:20px 28px;color:#fff'>"
        "<div style='font-size:18px;font-weight:700'>📈 " + node_label + " 盘中信号确认</div>"
        "<div style='font-size:13px;margin-top:4px;opacity:.85'>" + now_str + "</div></div>"
        "<div style='padding:24px 28px'>"
        "<table width='100%' cellpadding='0' cellspacing='0'"
        " style='border-collapse:collapse;font-size:13px'>"
        "<tr style='background:#f9fafb;color:#6b7280;font-size:12px'>"
        "<th style='padding:8px;text-align:left'>标的</th>"
        "<th style='padding:8px;text-align:left'>代码</th>"
        "<th style='padding:8px;text-align:center'>日线概率</th>"
        "<th style='padding:8px;text-align:right'>现价</th>"
        "<th style='padding:8px;text-align:right'>涨跌幅</th>"
        "<th style='padding:8px;text-align:left'>确认原因</th>"
        "</tr>" + rows + "</table></div>"
        "<div style='background:#f9fafb;padding:14px 28px;"
        "font-size:12px;color:#9ca3af;border-top:1px solid #f3f4f6'>"
        "以上标的同时满足日线模型做多信号和" + node_label
        + "盘中条件。仅供参考，注意仓位控制。</div>"
        "</div></body></html>"
    )
    return subject, html


# ── 对外接口 ──────────────────────────────────────────────────

def push_daily_report(signals, forward=5, portfolio=None, email=None, subject_prefix=""):
    """格式化日报并发送邮件。email: 收件人地址。subject_prefix: 主题前缀，如"【周一预报】"。"""
    user_name = getattr(getattr(portfolio, "user", None), "name", "")
    subject, html = _html_daily(signals, forward, portfolio, user_name)
    if subject_prefix:
        subject = subject_prefix + subject

    label = ("[" + user_name + "] ") if user_name else ""
    print("\n" + label + subject)
    print("  信号数: " + str(len(signals)))

    recipient = email
    if not recipient:
        cfg = _load_smtp_config()
        recipient = cfg["sender"] if cfg else None

    if not recipient:
        print("[邮件] 无收件人地址，跳过发送")
        return False

    return send_email(recipient, subject, html)


def push_intraday_report(node_label, confirmed, email):
    """发送盘中确认邮件给指定收件人。"""
    subject, html = _html_intraday(node_label, confirmed)
    print("  盘中推送 -> " + email + ": " + subject)
    return send_email(email, subject, html)
