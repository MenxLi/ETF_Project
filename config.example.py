# ── 邮件推送配置（163 SMTP）──────────────────────────────────────
# 复制本文件为 config.py 并填入真实值
SMTP_SENDER   = "your_email@163.com"
SMTP_PASSWORD = "your_163_smtp_auth_code"   # 授权码，非登录密码
SMTP_HOST     = "smtp.163.com"
SMTP_PORT     = 465                          # SSL

# ── Web 管理界面 ───────────────────────────────────────────────
WEB_PASSWORD  = "change_me"

# ── 数据配置 ──────────────────────────────────────────────────
DEFAULT_HISTORY_YEARS = 3
REALTIME_INTERVAL_MIN = 5

# ── Tushare 历史数据 ───────────────────────────────────────────
TUSHARE_TOKEN = "your_tushare_token_here"
