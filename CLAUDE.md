# ETF 量化管理平台 · 项目说明（供 Claude 读取）

> 本文件供 AI 助手快速了解项目现状，请在每次重大改动后同步更新。
> 最后更新：2026-06-24（B1 持仓实时价/浮盈 + B1a 卖出信号角标 + B1b 快速加仓/减持）

---

## 一、项目概览

面向多用户的 ETF 量化投资管理平台。后端用 Flask 提供 REST API，前端是 Vue 3 SPA，通过量化模型（LightGBM）每日生成买入 / 卖出信号，并支持盘中价格告警、模拟盘胜率追踪、历史回测等功能。

**运行方式**
```bash
# Windows 本地
cd D:\AI_PROJECT
.venv\Scripts\python.exe web_app.py   # 启动后访问 http://localhost:8888

# Linux 服务器
cd /workspace/suiy/etf
python web_app.py                      # 后台：nohup python web_app.py > app.log 2>&1 &
```

**部署流程**：本地开发 → `git push`（Windows PowerShell）→ 服务器 `git pull` → 重启 Flask。
服务器访问 GitHub 网络不稳定，统一从 Windows 本地 push。

---

## 二、技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.11 + Flask，Blueprint 拆分（`web_app.py` + `routes/`） |
| 前端 | Vue 3 + Vite + Tailwind CSS，SPA |
| 模型 | LightGBM 分类器 + 概率校准（Isotonic） |
| 行情数据 | Tushare Pro（历史日线），新浪财经 hq_str（实时价） |
| 定时任务 | Windows 任务计划程序，`setup_scheduler.ps1` 注册 |

---

## 三、目录结构

```
D:\AI_PROJECT\
├── web_app.py                  # Flask 入口（app 初始化、Blueprint 注册、SPA 路由）
├── routes/                     # API Blueprint 拆分（E1，2026-06-24）
│   ├── __init__.py
│   ├── _shared.py              # 跨 Blueprint 共用：路径常量、read/write 帮助函数、认证装饰器
│   ├── auth.py                 # /api/auth/*
│   ├── portfolio.py            # /api/portfolio/* /api/transactions/* /api/users/*
│   ├── signals.py              # /api/signals /api/sell-signals /api/alerts /api/signal-history /api/paper-trades
│   ├── admin.py                # /api/model-config /api/backtest /api/email-log /api/system-status
│   └── market.py               # /api/realtime-price /api/etf-list /api/etf-history /api/watchlist
├── run_daily.py                # 收盘后日任务入口（更新行情 → 生成买入信号 → 生成卖出信号 → 发邮件）
├── run_intraday.py             # 盘中监控入口（每 30 分钟由任务计划调用）
├── run_weekly.py               # 周任务（模型重训练）
├── run_monthly.py              # 月任务（Optuna 调参）
├── setup_scheduler.ps1         # 注册 Windows 任务计划（需管理员权限运行）
├── requirements.txt
├── config.py                   # 敏感配置（已 gitignore，不提交）
├── config.example.py           # 配置模板
├── CHANGELOG.md                # 版本日志
│
├── quant/
│   ├── data/
│   │   ├── tushare_client.py           # Tushare Pro 统一封装（单例 + 限速 + 超时 + 重试，E4c）
│   │   ├── fetch_historical.py         # Tushare 拉取历史行情（调用 tushare_client）
│   │   ├── realtime_monitor.py         # 新浪实时行情拉取
│   │   └── historical/*.parquet        # 各 ETF 历史数据（已 gitignore）
│   ├── features/
│   │   └── engineer.py                 # 技术指标特征工程
│   ├── models/
│   │   ├── trainer.py                  # 模型训练（E4b：保存带日期版本，更新 active_models）
│   │   ├── tuner.py                    # Optuna 超参调优
│   │   └── saved/                      # 训练好的模型文件，如 lgbm_forward5_20260624.pkl（已 gitignore）
│   ├── signals/
│   │   ├── generator.py                # 买入信号生成器
│   │   ├── sell_generator.py           # 卖出信号生成器（v1.5）
│   │   ├── price_monitor.py            # 盘中价格告警（v1.5）
│   │   ├── intraday.py                 # 盘中节点处理
│   │   ├── calibrator.py               # 概率校准
│   │   ├── notifier.py                 # 邮件推送
│   │   ├── paper_trader.py             # 模拟盘胜率计算
│   │   ├── model_config.json           # 模型参数配置（入库，多环境同步）
│   │   ├── candidates.json             # 当日买入信号（运行时，已 gitignore）
│   │   ├── sell_candidates.json        # 当日卖出信号（运行时，已 gitignore）
│   │   ├── alerts.json                 # 盘中价格告警（运行时，已 gitignore）
│   │   ├── thresholds.json             # 止损止盈阈值（运行时，已 gitignore）
│   │   ├── paper_trades.json           # 模拟盘记录（运行时，已 gitignore）
│   │   └── history/                    # 历史信号（运行时，已 gitignore）
│   ├── backtest/
│   │   └── runner.py
│   ├── portfolio/
│   │   └── manager.py                  # 持仓信号叠加逻辑，读取止损止盈配置
│   └── utils/
│       └── etf_list.py                 # ETF 代码名称映射
│
├── portfolios/                         # 用户数据（已 gitignore）
│   ├── users.json                      # 用户账号（含密码 hash）
│   └── {user_id}.json                  # 各用户持仓 + 交易记录
│
├── static/dist/                        # 前端构建产物（Vite 输出，入库）
│   ├── index.html
│   └── assets/
│
├── logs/                               # 运行日志（已 gitignore）
│   ├── daily_YYYY-MM-DD.jsonl          # 日任务结构化日志（E4a，每阶段一行 JSON）
│   └── email_log.jsonl                 # 邮件推送记录
├── reports/                            # 回测报告（已 gitignore）
│
└── frontend/                           # Vue 3 前端源码
    ├── src/
    │   ├── App.vue                     # 根组件，顶部导航栏 + 页面路由
    │   ├── main.js
    │   ├── store.js                    # 全局状态（用户信息、isAdmin）
    │   ├── api.js                      # 统一 fetch 封装
    │   ├── style.css
    │   ├── components/
    │   │   ├── SignalCard.vue           # 信号卡片组件
    │   │   ├── EtfSearch.vue            # ETF 搜索组件
    │   │   ├── AlgoExplainer.vue        # 算法说明组件
    │   │   ├── TodaySignalTab.vue       # 今日信号 Tab（自包含，含轮询）
    │   │   ├── SellSignalTab.vue        # 卖出信号 + 盘中价格告警 Tab
    │   │   ├── PaperTradeTab.vue        # 模拟盘胜率 Tab
    │   │   ├── PositionTab.vue          # 持仓明细表格（实时价/浮盈列、卖出信号 badge、快速加仓/减持气泡）+ 导入/编辑弹窗
    │   │   └── TransactionTab.vue       # 交易记录表格 + 新增弹窗（含自动拉实时价）
    │   └── views/
    │       ├── SignalView.vue           # 信号看板（含买入/卖出/历史/模拟盘/算法）
    │       ├── PortfolioView.vue        # 持仓管理（切换账户时并发拉实时价 + 卖出信号；5 张汇总卡片）
    │       ├── ModelView.vue            # 模型调参（管理员）
    │       ├── EtfView.vue             # ETF 行情
    │       ├── BacktestView.vue         # 回测结果（管理员）
    │       ├── EmailView.vue            # 邮件记录（管理员）
    │       ├── SystemView.vue           # 系统状态（管理员）
    │       └── LoginView.vue            # 登录页
    └── vite.config.js
```

---

## 四、前端构建

```bash
cd D:\AI_PROJECT\frontend

npm run build               # 正常构建（输出至 ../static/dist/）
npx vite build --emptyOutDir false  # 服务器文件被锁时用此命令
```

**注意**：`static/dist/` 已入库，服务器 pull 后无需重新构建。

---

## 五、App 导航页面

`App.vue` 中的顶部 Tab（`adminOnly: true` 仅管理员可见）：

| key | 页面 | 权限 |
|---|---|---|
| `portfolio` | 持仓管理 | 所有用户 |
| `signals` | 信号看板 | 所有用户 |
| `market` | ETF 行情 | 所有用户 |
| `model` | 模型调参 | 管理员 |
| `backtest` | 回测结果 | 管理员 |
| `emails` | 邮件记录 | 管理员 |
| `system` | 系统状态 | 管理员 |

---

## 六、信号看板 Sub-Tab（SignalView.vue）

```javascript
const TABS = [
  { key: 'today',   label: '📡 今日信号' },
  { key: 'sell',    label: '🔴 卖出信号' },
  { key: 'history', label: '🗂 历史档案' },
  { key: 'paper',   label: '📊 模拟盘胜率' },
  { key: 'algo',    label: '📖 算法说明' },
]
```

Tab 顺序已于 2026-06-24 修正（待办 #14 已完成）。各 Tab 内容已拆分为独立子组件（E2a）。

---

## 七、model_config.json 关键参数

```json
{
  "prob_threshold": 0.5,        // 买入信号概率阈值
  "blacklist": [...],            // 黑名单 ETF（不生成信号）
  "threshold_overrides": {},     // 个别 ETF 阈值覆盖
  "stop_loss": 0.05,            // 止损线（浮亏 5% 触发卖出建议）
  "take_profit": 0.08,          // 止盈线（浮盈 8% 触发卖出建议）
  "sell_prob_threshold": 0.55,  // 模型看空阈值（prob_down > 55% 触发）
  "active_models": {            // 当前激活模型版本（E4b，trainer.py 训练后自动写入）
    "5": "lgbm_forward5_20260624.pkl"
  }
}
```

---

## 八、定时任务（Windows 任务计划）

| 任务名 | 时间 | 脚本 |
|---|---|---|
| `Quant_Open` | 工作日 09:25 | intraday --node open |
| `Quant_Amend` | 工作日 11:25 | intraday --node amend |
| `Quant_PM` | 工作日 13:05 | intraday --node pm |
| `Quant_Close` | 工作日 14:50 | intraday --node close |
| `Quant_Daily` | 工作日 15:35 | run_daily.py |
| `Quant_Monitor` | 工作日 09:30~14:30 每 30 分钟 | run_intraday.py |
| `Quant_Weekly` | 周日 10:00 | run_weekly.py |
| `Quant_Monthly` | 周日 12:00 | run_monthly.py |

重新注册定时任务：以管理员身份在 PowerShell 运行 `.\setup_scheduler.ps1`

---

## 九、主要 API 端点

### 认证
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET  /api/auth/me`
- `POST /api/auth/change-password`

### 买入信号
- `GET  /api/signals` — 当日买入信号
- `POST /api/run-signals` — 管理员手动触发信号生成
- `GET  /api/run-signals/status` — 生成任务进度
- `GET  /api/signal-history` — 历史日期列表
- `GET  /api/signal-history/<date>` — 某日历史信号

### 卖出信号（v1.5）
- `GET  /api/sell-signals` — 当前用户卖出信号（STOP_LOSS / TAKE_PROFIT / MODEL_SELL）
- `POST /api/sell-signals/run` — 管理员手动触发卖出信号生成

### 盘中价格告警（v1.5）
- `GET  /api/alerts` — 当前用户告警列表
- `POST /api/alerts/<id>/dismiss` — 标记单条告警已读
- `POST /api/alerts/dismiss-all` — 全部标记已读
- `POST /api/alerts/run` — 管理员手动触发盘中监控

### 持仓 & 交易
- `GET/PUT /api/portfolio/<user_id>`
- `POST    /api/portfolio/<user_id>/positions` — 导入初始持仓
- `DELETE  /api/portfolio/<user_id>/positions/<code>`
- `GET/POST /api/transactions/<user_id>`
- `DELETE   /api/transactions/<user_id>/<tx_id>`

### 模型配置（管理员）
- `GET/PUT /api/model-config`
- `POST    /api/model-config/recalibrate`

### 模型版本管理（管理员，E4b）
- `GET  /api/model-versions` — 列出 saved/ 下所有版本文件，标记 is_active
- `POST /api/model-versions/activate` — 将指定文件写入 active_models，即时生效

### 其他
- `GET  /api/paper-trades` — 模拟盘胜率数据
- `POST /api/paper-trades/refresh`
- `GET  /api/realtime-price/<code>` — 新浪实时价
- `GET  /api/etf-list` — ETF 列表
- `GET  /api/backtest`
- `GET  /api/email-log`
- `GET  /api/system-status`

---

## 十、用户权限

- **管理员**：用户名 `suiy`，可访问所有页面和管理员 API
- **普通用户**：只能看自己的持仓和信号，不能访问 model/backtest/email/system 页面

`portfolios/users.json` 存储用户列表，密码用 `werkzeug.security.generate_password_hash` 哈希存储。

---

## 十一、当前版本与待办

**当前版本**：v1.7（2026-06-24）

**近期待办**（详见 TODO.md）：
- [ ] **B3**：已实现盈亏追踪（卖出实现盈亏、累计汇总卡片）
- [ ] **B4**：持仓仓位可视化（权重进度条 + 板块饼图）
- [ ] **B5**：交易记录筛选 & 汇总

**已完成**：
- v1.5 卖出信号系统（2026-06-23）
- **C1** ETF 票池扩充：`etf_list.py` 从 26 只扩至 61 只，新增银行/保险/AI/机器人/家电/食品饮料/化工/石油/创新药/医疗器械/北证50/中证2000 等 35 只，新增「海外」分类（中概互联/纳指100/恒生科技/标普500）（2026-06-24）
- **C2** ETF 分类体系细化：11 分类（宽基/海外/金融/医疗/科技/能源/消费/周期/地产/债券/商品），`/api/etf-list` 新增 categories 字段，`store.etfCategories` 全局可用；行情页侧栏折叠分组、信号页分类筛选条（2026-06-24）
- **C3** 历史数据补拉 & 模型重训练：`fetch_historical --skip-existing` 补拉新增 35 只（全成功），重训练后数据集 18,876→39,719 行（2.1×），信号覆盖量 26→61 只，激活模型 `lgbm_forward5_20260624.pkl`（2026-06-24）
- **E1** 后端 Blueprint 拆分：`web_app.py` 951 行 → 94 行入口 + `routes/` 5 个 Blueprint（2026-06-24）
- **E2a** SignalView.vue 子组件拆分：931→320 行，含 Tab 顺序修复（2026-06-24）
- **E2b** PortfolioView.vue 子组件拆分：950→280 行（2026-06-24）
- **E4a** 日任务错误恢复：`run_daily.py` 各阶段独立 try/except + 指数退避重试（3次，5→10→20s）+ 结构化日志 `logs/daily_YYYY-MM-DD.jsonl`（2026-06-24）
- **E4b** 模型版本管理：`trainer.py` 保存带日期版本（`lgbm_forward5_YYYYMMDD.pkl`），`model_config.json` 新增 `active_models`，`/api/model-versions` + `ModelView` Section 04 支持一键激活/回滚（2026-06-24）
- **E4c** Tushare 调用封装：新建 `quant/data/tushare_client.py` 单例（限速 0.5s/call + 超时 30s + 指数退避重试 3次），`fetch_historical.py` 和 `generator.py` 统一改用 `pro_bar()` 封装（2026-06-24）
- **B1** 持仓明细实时价/浮盈：现价/现值/浮盈/浮盈% 4 列（绿涨红跌），顶部 5 张卡片（总资产/现金/持仓市值/总浮盈/品种）（2026-06-24）
- **B1a** 卖出信号角标：PortfolioView 切换账户时并发拉 `/api/sell-signals`，ETF 名旁显示「止损/止盈/看空」badge（2026-06-24）
- **B1b** 快速加仓/减持：操作列 +加仓/-减持 按钮，行内气泡表单（股数+价格+预览扣款/到账+现金变化），回车确认；底层调 `POST /api/transactions`（2026-06-24）
- **B2** 交易→持仓联动：后端 `api_create_transaction` 已完整实现（持仓股数/均价/现金三联动），B1b 提供前端快捷入口（2026-06-24）

---

## 十二、常见操作备忘

```bash
# 前端开发模式（热更新）
cd D:\AI_PROJECT\frontend && npm run dev

# 前端构建（生产）
cd D:\AI_PROJECT\frontend && npm run build

# 查看 Flask 进程（服务器）
ps aux | grep web_app

# 重启 Flask（服务器）
kill <PID> && nohup python web_app.py > app.log 2>&1 &

# 手动运行日任务（测试）
python run_daily.py

# 手动运行盘中监控（测试）
python run_intraday.py
```
