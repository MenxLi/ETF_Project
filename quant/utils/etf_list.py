# 主流 A 股 ETF 标的列表（v1.8，61 只）
# 分类：宽基 / 海外 / 金融 / 医疗 / 科技 / 能源 / 消费 / 周期 / 地产 / 债券 / 商品

ETF_LIST = [
    # ── 宽基指数（国内）─────────────────────────────────────────
    {"code": "510050", "name": "上证50ETF",          "category": "宽基"},
    {"code": "510180", "name": "上证180ETF",         "category": "宽基"},
    {"code": "510300", "name": "沪深300ETF",         "category": "宽基"},
    {"code": "510500", "name": "中证500ETF",         "category": "宽基"},
    {"code": "159901", "name": "深证100ETF",         "category": "宽基"},
    {"code": "159915", "name": "创业板ETF",          "category": "宽基"},
    {"code": "159922", "name": "中证500ETF(深)",     "category": "宽基"},
    {"code": "159949", "name": "创业板50ETF",        "category": "宽基"},
    {"code": "512100", "name": "中证1000ETF",        "category": "宽基"},
    {"code": "563300", "name": "中证2000ETF",        "category": "宽基"},
    {"code": "588000", "name": "科创50ETF",          "category": "宽基"},
    {"code": "159834", "name": "北证50ETF",          "category": "宽基"},

    # ── 宽基指数（海外）─────────────────────────────────────────
    {"code": "513050", "name": "中概互联ETF",        "category": "海外"},
    {"code": "513100", "name": "纳斯达克100ETF",     "category": "海外"},
    {"code": "513130", "name": "恒生科技ETF",        "category": "海外"},
    {"code": "513500", "name": "标普500ETF",         "category": "海外"},

    # ── 金融 ──────────────────────────────────────────────────
    {"code": "512000", "name": "券商ETF",            "category": "金融"},
    {"code": "512070", "name": "保险ETF",            "category": "金融"},
    {"code": "512800", "name": "银行ETF",            "category": "金融"},
    {"code": "512880", "name": "证券ETF",            "category": "金融"},

    # ── 医疗 ──────────────────────────────────────────────────
    {"code": "512010", "name": "医药ETF",            "category": "医疗"},
    {"code": "512170", "name": "医疗ETF",            "category": "医疗"},
    {"code": "159883", "name": "医疗器械ETF",        "category": "医疗"},
    {"code": "159992", "name": "创新药ETF",          "category": "医疗"},

    # ── 科技 ──────────────────────────────────────────────────
    {"code": "159806", "name": "网络安全ETF",        "category": "科技"},
    {"code": "159995", "name": "芯片ETF",            "category": "科技"},
    {"code": "512480", "name": "半导体ETF",          "category": "科技"},
    {"code": "515050", "name": "5G ETF",             "category": "科技"},
    {"code": "515070", "name": "AI ETF",             "category": "科技"},
    {"code": "516510", "name": "云计算ETF",          "category": "科技"},
    {"code": "562500", "name": "机器人ETF",          "category": "科技"},

    # ── 能源 ──────────────────────────────────────────────────
    {"code": "159611", "name": "电力ETF",            "category": "能源"},
    {"code": "159628", "name": "石油ETF",            "category": "能源"},
    {"code": "159869", "name": "新能源车ETF",        "category": "能源"},
    {"code": "159931", "name": "碳中和ETF",          "category": "能源"},
    {"code": "515790", "name": "光伏ETF",            "category": "能源"},
    {"code": "516160", "name": "新能源ETF",          "category": "能源"},
    {"code": "562900", "name": "储能ETF",            "category": "能源"},

    # ── 消费 ──────────────────────────────────────────────────
    {"code": "159766", "name": "旅游ETF",            "category": "消费"},
    {"code": "159928", "name": "消费ETF",            "category": "消费"},
    {"code": "159996", "name": "家电ETF",            "category": "消费"},
    {"code": "512690", "name": "酒ETF",              "category": "消费"},
    {"code": "512980", "name": "传媒ETF",            "category": "消费"},
    {"code": "515170", "name": "食品饮料ETF",        "category": "消费"},

    # ── 周期 ──────────────────────────────────────────────────
    {"code": "159825", "name": "农业ETF",            "category": "周期"},
    {"code": "515210", "name": "钢铁ETF",            "category": "周期"},
    {"code": "515220", "name": "煤炭ETF",            "category": "周期"},
    {"code": "515600", "name": "央企改革ETF",        "category": "周期"},
    {"code": "516020", "name": "化工ETF",            "category": "周期"},
    {"code": "516780", "name": "环保ETF",            "category": "周期"},
    {"code": "516950", "name": "基建ETF",            "category": "周期"},
    {"code": "516970", "name": "军工ETF",            "category": "周期"},

    # ── 地产 ──────────────────────────────────────────────────
    {"code": "512200", "name": "房地产ETF",          "category": "地产"},
    {"code": "515000", "name": "地产ETF",            "category": "地产"},

    # ── 债券 ──────────────────────────────────────────────────
    {"code": "511010", "name": "国债ETF",            "category": "债券"},
    {"code": "511090", "name": "30年国债ETF",        "category": "债券"},
    {"code": "511380", "name": "可转债ETF",          "category": "债券"},

    # ── 商品 ──────────────────────────────────────────────────
    {"code": "159812", "name": "白银ETF",            "category": "商品"},
    {"code": "159980", "name": "有色金属ETF",        "category": "商品"},
    {"code": "159985", "name": "豆粕ETF",            "category": "商品"},
    {"code": "518880", "name": "黄金ETF",            "category": "商品"},
]

# 分类展示顺序
CATEGORY_ORDER = ["宽基", "海外", "金融", "医疗", "科技", "能源", "消费", "周期", "地产", "债券", "商品"]

# ETF 交易所规则：
#   上交所(SH)：510xxx 511xxx 512xxx 513xxx 515xxx 516xxx 518xxx 56xxxx 588xxx
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

# 代码 → 分类映射
ETF_CATEGORIES = {e["code"]: e["category"] for e in ETF_LIST}

# yfinance代码 → 原始代码
YF_TO_CODE = {_yf_code(e["code"]): e["code"] for e in ETF_LIST}
