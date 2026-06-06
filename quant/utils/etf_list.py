# 主流 A 股 ETF 标的列表
# 覆盖宽基指数、行业、主题、债券、商品类 ETF

ETF_LIST = [
    # ── 宽基指数 ──────────────────────────────────────────────
    {"code": "510300", "name": "沪深300ETF",      "category": "宽基"},
    {"code": "510500", "name": "中证500ETF",      "category": "宽基"},
    {"code": "588000", "name": "科创50ETF",       "category": "宽基"},
    {"code": "159915", "name": "创业板ETF",       "category": "宽基"},
    {"code": "512100", "name": "中证1000ETF",     "category": "宽基"},
    {"code": "510050", "name": "上证50ETF",       "category": "宽基"},
    {"code": "159922", "name": "中证500ETF(深)",  "category": "宽基"},

    # ── 行业 / 主题 ───────────────────────────────────────────
    {"code": "512010", "name": "医药ETF",         "category": "行业"},
    {"code": "512200", "name": "房地产ETF",       "category": "行业"},
    {"code": "512880", "name": "证券ETF",         "category": "行业"},
    {"code": "515000", "name": "地产ETF",         "category": "行业"},
    {"code": "512690", "name": "酒ETF",           "category": "行业"},
    {"code": "516160", "name": "新能源ETF",       "category": "行业"},
    {"code": "159869", "name": "新能源车ETF",     "category": "行业"},
    {"code": "512480", "name": "半导体ETF",       "category": "行业"},
    {"code": "159995", "name": "芯片ETF",         "category": "行业"},
    {"code": "515790", "name": "光伏ETF",         "category": "行业"},
    {"code": "512170", "name": "医疗ETF",         "category": "行业"},
    {"code": "159766", "name": "旅游ETF",         "category": "行业"},
    {"code": "512000", "name": "券商ETF",         "category": "行业"},
    {"code": "159928", "name": "消费ETF",         "category": "行业"},
    {"code": "515220", "name": "煤炭ETF",         "category": "行业"},
    {"code": "516970", "name": "军工ETF",         "category": "行业"},

    # ── 债券 / 商品 ───────────────────────────────────────────
    {"code": "511010", "name": "国债ETF",         "category": "债券"},
    {"code": "518880", "name": "黄金ETF",         "category": "商品"},
    {"code": "159980", "name": "有色金属ETF",     "category": "商品"},
]

# ETF 交易所规则：
#   上交所(SS)：510xxx 511xxx 512xxx 515xxx 516xxx 518xxx 588xxx
#   深交所(SZ)：159xxx
# 简单判断：以 "159" 开头 → 深交所，其余以 "5" 开头 → 上交所
def _is_sh(code: str) -> bool:
    return code.startswith("5") and not code.startswith("159")

def _yf_code(code: str) -> str:
    return code + (".SS" if _is_sh(code) else ".SZ")

def _bs_code(code: str) -> str:
    return ("sh." if _is_sh(code) else "sz.") + code

# 仅代码列表，便于批量查询
ETF_CODES = [e["code"] for e in ETF_LIST]

# yfinance 格式代码列表（510300.SS / 159915.SZ）
ETF_YF_CODES = [_yf_code(e["code"]) for e in ETF_LIST]

# 代码 → 名称映射
CODE_TO_NAME = {e["code"]: e["name"] for e in ETF_LIST}

# yfinance代码 → 原始代码
YF_TO_CODE = {_yf_code(e["code"]): e["code"] for e in ETF_LIST}
