# ETF Quant 接口文档 / API Reference

> Base URL: `http://localhost:5000`  
> 所有接口均使用 Cookie Session 认证。未登录访问受保护接口返回 `401`。  
> All endpoints use Cookie Session authentication. Unauthenticated requests to protected routes return `401`.

---

## 目录 / Contents

- [认证 Auth](#认证-auth)
- [ETF 行情 Market](#etf-行情-market)
- [自选列表 Watchlist](#自选列表-watchlist)
- [用户管理 Users](#用户管理-users-管理员)
- [持仓管理 Portfolio](#持仓管理-portfolio)
- [交易记录 Transactions](#交易记录-transactions)
- [信号 Signals](#信号-signals)
- [模型配置 Model Config](#模型配置-model-config-管理员)
- [回测 Backtest](#回测-backtest-管理员)
- [系统状态 System](#系统状态-system-管理员)
- [邮件日志 Email Log](#邮件日志-email-log-管理员)

---

## 认证 Auth

### POST `/api/auth/login`

登录，建立 Session。

**Request Body**
```json
{
  "username": "admin",
  "password": "your_password"
}
```

**Response 200**
```json
{
  "id": "abc123",
  "name": "Suiy",
  "role": "admin",
  "email": "user@example.com"
}
```

**Response 401**
```json
{ "error": "用户名或密码错误" }
```

---

### POST `/api/auth/logout`

登出，清除 Session。

**Response 200**
```json
{ "ok": true }
```

---

### GET `/api/auth/me`

获取当前登录用户信息。

**Response 200**
```json
{
  "id": "abc123",
  "name": "Suiy",
  "role": "admin",
  "email": "user@example.com"
}
```

**Response 401** — 未登录

---

### POST `/api/auth/change-password`

修改当前用户密码。

**Request Body**
```json
{
  "old_password": "old",
  "new_password": "new_secure_password"
}
```

**Response 200**
```json
{ "ok": true }
```

**Response 400**
```json
{ "error": "旧密码错误" }
```

---

### POST `/api/users/<user_id>/reset-password`  🔐 管理员

重置指定用户密码。

**Request Body**
```json
{ "new_password": "reset123" }
```

**Response 200**
```json
{ "ok": true }
```

---

## ETF 行情 Market

### GET `/api/etf-list`  🔑 需登录

获取系统追踪的所有 ETF 列表。

**Response 200**
```json
{
  "159915": "创业板ETF",
  "510300": "沪深300ETF",
  "512010": "医疗ETF"
}
```

---

### GET `/api/etf-history/<code>`  🔑 需登录

获取指定 ETF 最近 365 个交易日的 OHLCV 数据。

**Path Parameters**

| 参数 | 说明 |
|------|------|
| `code` | ETF 代码，如 `510300` |

**Response 200**
```json
[
  {
    "date":   "2025-06-05",
    "close":  4.52,
    "open":   4.48,
    "high":   4.55,
    "low":    4.46,
    "volume": 123456789.0
  }
]
```

---

## 自选列表 Watchlist

### GET `/api/watchlist`  🔑 需登录

获取当前用户的自选 ETF 代码列表。

**Response 200**
```json
["510300", "159915", "512010"]
```

---

### PUT `/api/watchlist`  🔑 需登录

更新当前用户的自选列表（全量替换）。

**Request Body**
```json
["510300", "159915"]
```

**Response 200**
```json
["510300", "159915"]
```

---

## 用户管理 Users  🔐 管理员

### GET `/api/users`

获取所有用户列表。

**Response 200**
```json
[
  {
    "id":             "abc123",
    "name":           "Suiy",
    "role":           "admin",
    "email":          "user@example.com",
    "portfolio_file": "portfolios/suiy.json",
    "active":         true
  }
]
```

---

### POST `/api/users`

新增用户。

**Request Body**
```json
{
  "name":     "张三",
  "email":    "zhangsan@example.com",
  "password": "init_password",
  "role":     "user"
}
```

**Response 201**
```json
{
  "id":   "xyz789",
  "name": "张三",
  "role": "user",
  "email": "zhangsan@example.com"
}
```

---

### PUT `/api/users/<user_id>`

更新用户信息（名称、邮箱、激活状态）。

**Request Body**（字段均可选）
```json
{
  "name":   "新名称",
  "email":  "new@example.com",
  "active": false
}
```

**Response 200** — 返回更新后的用户对象

---

### DELETE `/api/users/<user_id>`

删除用户（同时删除其持仓文件）。

**Response 200**
```json
{ "ok": true }
```

---

## 持仓管理 Portfolio

> 普通用户只能访问自己的数据；管理员可访问任意用户。

### GET `/api/portfolio/<user_id>`  🔑 需登录

获取用户持仓信息。

**Response 200**
```json
{
  "cash":             50000.0,
  "max_position_pct": 0.20,
  "max_sector_pct":   0.40,
  "positions": [
    {
      "code":       "510300",
      "name":       "沪深300ETF",
      "shares":     10000,
      "cost_price": 4.20,
      "buy_date":   "2025-01-15"
    }
  ],
  "watchlist":  ["159915"],
  "updated_at": "2025-06-05 15:40:00"
}
```

---

### PUT `/api/portfolio/<user_id>`  🔑 需登录

更新持仓基本参数（资金、仓位上限）。

**Request Body**（字段均可选）
```json
{
  "cash":             80000.0,
  "max_position_pct": 0.25,
  "max_sector_pct":   0.50
}
```

**Response 200** — 返回更新后的完整持仓对象

---

### POST `/api/portfolio/<user_id>/positions`  🔑 需登录

新增或更新一只 ETF 持仓（以 `code` 为主键，存在则覆盖）。

**Request Body**
```json
{
  "code":       "512010",
  "name":       "医疗ETF",
  "shares":     5000,
  "cost_price": 1.85,
  "buy_date":   "2025-05-20"
}
```

**Response 200** — 返回该持仓对象

---

### DELETE `/api/portfolio/<user_id>/positions/<code>`  🔑 需登录

删除一只 ETF 持仓。

**Response 204** — 无响应体

---

## 交易记录 Transactions

### GET `/api/transactions/<user_id>`  🔑 需登录

获取用户所有交易记录（最新在前）。

**Response 200**
```json
[
  {
    "id":         "tx_20250605_153012_00",
    "date":       "2025-06-05",
    "action":     "buy",
    "etf_code":   "510300",
    "etf_name":   "沪深300ETF",
    "shares":     5000,
    "price":      4.52,
    "amount":     22600.0,
    "note":       "模型信号买入",
    "created_at": "2025-06-05 15:30:12"
  }
]
```

---

### POST `/api/transactions/<user_id>`  🔑 需登录

新增交易记录。

**Request Body**
```json
{
  "date":     "2025-06-05",
  "action":   "buy",
  "etf_code": "510300",
  "etf_name": "沪深300ETF",
  "shares":   5000,
  "price":    4.52,
  "note":     "模型信号买入"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `action` | string | 是 | `"buy"` 或 `"sell"` |
| `etf_code` | string | 是 | ETF 代码 |
| `shares` | number | 是 | 股数 |
| `price` | number | 是 | 成交价 |
| `date` | string | 否 | 默认今日 |
| `note` | string | 否 | 备注 |

**Response 201** — 返回创建的交易记录对象

---

### DELETE `/api/transactions/<user_id>/<tx_id>`  🔑 需登录

删除一条交易记录。

**Response 204** — 无响应体  
**Response 404** — 记录不存在

---

## 信号 Signals

### GET `/api/signals`  🔑 需登录

获取最新一期信号候选池（叠加当前用户的持仓感知建议）。

**Response 200**
```json
{
  "trade_date":   "2025-06-05",
  "generated_at": "2025-06-05 15:36:12",
  "count":        5,
  "signals": [
    {
      "code":       "510300",
      "name":       "沪深300ETF",
      "close":      4.52,
      "prob_up":    0.7823,
      "suggestion": "建议买入",
      "reason":     "概率较高，当前未持仓"
    }
  ]
}
```

---

### GET `/api/signal-history`  🔑 需登录

获取有历史信号记录的日期列表（最近 90 天，降序）。

**Response 200**
```json
["2025-06-05", "2025-06-04", "2025-06-03"]
```

---

### GET `/api/signal-history/<date>`  🔑 需登录

获取指定日期的历史信号（叠加当前用户的个性化建议）。

**Path Parameters**

| 参数 | 说明 |
|------|------|
| `date` | 格式 `YYYY-MM-DD` |

**Response 200** — 同 `/api/signals` 结构  
**Response 400** — 日期格式错误  
**Response 404** — 该日期无记录

---

### GET `/api/signal-history/etf/<code>`  🔑 需登录

获取某只 ETF 历史上所有出现信号的日期及做多概率（用于 K 线图标记）。

**Response 200**
```json
[
  { "date": "2025-06-05", "prob_up": 0.7823, "close": 4.52 },
  { "date": "2025-05-20", "prob_up": 0.6541, "close": 4.31 }
]
```

---

## 模型配置 Model Config  🔐 管理员

### GET `/api/model-config`

获取当前模型参数配置和自动校准结果。

**Response 200**
```json
{
  "config": {
    "prob_threshold": 0.55,
    "blacklist": ["511010"],
    "threshold_overrides": {
      "open_vol_ratio_min": 1.2
    }
  },
  "calibrated": {
    "calibrated_at":       "2025-06-05 15:36:00",
    "lookback_days":       20,
    "open_vol_ratio_min":  1.18,
    "open_pct_min":        0.31,
    "amend_pct_min":       0.25,
    "amend_pct_max":       2.80,
    "pm_pct_min":          0.20,
    "pm_pct_max":          3.00,
    "close_strong_pct":    0.50,
    "close_dd_threshold":  0.80,
    "_market_vol_std":     0.72,
    "_market_atr_mean":    0.85,
    "_vol_ratio_p50":      1.05
  }
}
```

---

### PUT `/api/model-config`  🔐 管理员

更新模型参数配置。

**Request Body**（字段均可选）
```json
{
  "prob_threshold": 0.60,
  "blacklist": ["511010", "518880"],
  "threshold_overrides": {
    "open_vol_ratio_min": 1.30
  }
}
```

**约束**：`prob_threshold` 须在 `0.30 ~ 0.95` 之间，否则返回 `400`。

**Response 200** — 返回更新后的 config 对象

---

### POST `/api/model-config/recalibrate`  🔐 管理员

触发动态阈值自动校准。

**Request Body**
```json
{ "lookback": 20 }
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `lookback` | int | 回望交易日数，范围 5~120，默认 20 |

**Response 200**
```json
{
  "ok": true,
  "thresholds": {
    "calibrated_at": "2025-06-06 10:05:32",
    "open_vol_ratio_min": 1.18,
    ...
  }
}
```

**Response 500** — 校准失败，返回错误信息

---

## 回测 Backtest  🔐 管理员

### GET `/api/backtest`

获取历史回测结果列表。

**Response 200**
```json
[
  {
    "etf_code":    "510300",
    "forward_days": 5,
    "win_rate":    0.623,
    "total_return": 0.187,
    "sharpe":      1.42,
    "max_drawdown": -0.082
  }
]
```

---

## 系统状态 System  🔐 管理员

### GET `/api/system-status`

获取关键文件的存在状态和最后更新时间。

**Response 200**
```json
{
  "signals":    { "exists": true,  "last_modified": "2025-06-05 15:36:12" },
  "thresholds": { "exists": true,  "last_modified": "2025-06-05 15:35:50" },
  "users":      { "exists": true,  "last_modified": "2025-06-01 10:20:00" },
  "email_log":  { "exists": true,  "last_modified": "2025-06-05 15:37:01" },
  "models":     { "exists": true,  "last_modified": "2025-06-01 09:00:00" }
}
```

---

## 邮件日志 Email Log  🔐 管理员

### GET `/api/email-log`

获取最近 100 条邮件发送日志（最新在前）。

**Response 200**
```json
[
  {
    "timestamp": "2025-06-05 15:37:01",
    "recipient": "user@example.com",
    "subject":   "【ETF量化日报】2025-06-05 共 5 个信号",
    "status":    "success"
  }
]
```

---

## 错误码说明 / Error Codes

| HTTP 状态码 | 说明 |
|-------------|------|
| 200 | 成功 |
| 201 | 创建成功 |
| 204 | 删除成功（无响应体）|
| 400 | 请求参数错误 |
| 401 | 未登录或 Session 已过期 |
| 403 | 权限不足（需要管理员）|
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

---

## 认证说明 / Auth Notes

- 登录后服务端设置 `HttpOnly` Cookie，前端无需手动管理 Token
- Session 默认有效期：关闭浏览器后失效（`SESSION_PERMANENT = False`）
- 管理员（`role: "admin"`）可访问所有接口；普通用户只能访问自己的数据
- 图标说明：🔑 需登录 | 🔐 需管理员权限
