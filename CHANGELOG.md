# ETF 量化管理平台 · 更新日志

> 记录平台各版本的功能迭代与问题修复

---

## v1.7 · 2026-06-24

**持仓功能增强**

- **B1 实时持仓估值**：持仓明细表新增现价 / 现值 / 浮盈 / 浮盈% 四列，绿涨红跌配色；顶部新增 5 张汇总卡片（总资产 / 现金 / 持仓市值 / 总浮盈 / 品种数量）
- **B1a 卖出信号角标**：切换账户时并发拉取 `/api/sell-signals`，持仓表格 ETF 名旁显示「止损 / 止盈 / 看空」badge，一眼识别需关注的仓位
- **B1b 快速加仓 / 减持**：操作列新增「+加仓」「-减持」按钮，点击后展开行内气泡表单（股数 + 价格 + 扣款/到账预览 + 现金变化），回车即可确认；底层调用 `POST /api/transactions` 实现交易与持仓联动

**ETF 票池扩充（C1 / C2 / C3）**

- **C1** `etf_list.py` 从 26 只扩充至 61 只，新增银行 / 保险 / AI / 机器人 / 家电 / 食品饮料 / 化工 / 石油 / 创新药 / 医疗器械 / 北证50 / 中证2000 等 35 只，新增「海外」分类（中概互联 / 纳指100 / 恒生科技 / 标普500）
- **C2** ETF 分类体系细化为 11 类（宽基 / 海外 / 金融 / 医疗 / 科技 / 能源 / 消费 / 周期 / 地产 / 债券 / 商品）；`/api/etf-list` 新增 `categories` 字段，行情页侧栏支持折叠分组，信号页新增分类筛选条
- **C3** 使用 `fetch_historical --skip-existing` 补拉新增 35 只历史数据，重训练后数据集从 18,876 → 39,719 行（×2.1），信号覆盖量从 26 → 61 只，激活模型更新为 `lgbm_forward5_20260624.pkl`

**工程重构**

- **E1 后端 Blueprint 拆分**：`web_app.py` 从 951 行精简至 94 行入口，API 按业务域拆分至 `routes/` 下 5 个 Blueprint（auth / portfolio / signals / admin / market）
- **E2a SignalView 子组件拆分**：`SignalView.vue` 931 → 320 行，各 Tab 内容拆分为独立子组件（`TodaySignalTab` / `SellSignalTab` / `PaperTradeTab`），同步修正 Tab 顺序
- **E2b PortfolioView 子组件拆分**：`PortfolioView.vue` 950 → 280 行，持仓表格 / 交易记录拆出为 `PositionTab` / `TransactionTab`
- **E4a 日任务错误恢复**：`run_daily.py` 各阶段独立 try/except + 指数退避重试（3 次，5→10→20s），结构化日志写入 `logs/daily_YYYY-MM-DD.jsonl`
- **E4b 模型版本管理**：`trainer.py` 保存带日期版本文件（`lgbm_forward5_YYYYMMDD.pkl`），`model_config.json` 新增 `active_models` 字段，新增 `/api/model-versions` 端点 + ModelView 一键激活 / 回滚
- **E4c Tushare 调用封装**：新建 `quant/data/tushare_client.py` 单例（限速 0.5s/call + 超时 30s + 指数退避重试 3 次），`fetch_historical.py` 和 `generator.py` 统一改用封装接口

---

## v1.5 · 2026-06-23（卖出信号系统）

**已完成**

- [x] 止损止盈阈值（`stop_loss` / `take_profit`）从硬编码移入 `model_config.json`，模型调参页面新增止损（红）/ 止盈（绿）/ 模型看空门槛三个滑块控件
- [x] 新增 `quant/signals/sell_generator.py`：收盘后扫描所有用户持仓 ETF，跑模型取 `prob_down`，叠加止损 / 止盈 / 模型看空三层规则，按优先级生成每用户卖出候选列表，保存至 `sell_candidates.json`
- [x] `run_daily.py` 新增 Step 3/5 调用 `generate_sell_signals()`，与买入信号生成串联
- [x] 新增后端 API：`GET /api/sell-signals`（返回当前用户卖出信号）、`POST /api/sell-signals/run`（管理员手动触发）

- [x] 新增 `quant/signals/price_monitor.py`：批量拉新浪实时价（一次请求覆盖所有持仓 ETF）→ 检查止损止盈 → 写入 `alerts.json`，去重逻辑保证同一仓位同一触发类型当天只告警一次
- [x] 新增 `run_intraday.py`：盘中监控入口，自动判断交易时段（09:30–11:30 / 13:00–15:00）后调用 price_monitor
- [x] `setup_scheduler.ps1` 新增 `Quant_Monitor` 任务，工作日 09:30–14:30 每 30 分钟触发一次（共 9 个时间点）
- [x] 新增后端 API：`GET /api/alerts`（返回当前用户告警）、`POST /api/alerts/<id>/dismiss`（标记已读）、`POST /api/alerts/dismiss-all`、`POST /api/alerts/run`（管理员手动触发）

- [x] 信号看板新增"卖出信号"子 Tab：「收盘卖出建议」展示 sell_generator 生成的三类卖出信号（止损/止盈/模型看空），「盘中价格告警」展示 price_monitor 实时告警并支持逐条或全部标记已读；管理员可手动触发重新生成或盘中监控

---

## v1.4 · 2026-06-12

**Bug 修复**

- 修复新增交易弹窗中手动搜索 ETF 时无法自动拉取实时价的问题：通过 `watch` 监听 `etf_code` 变化，覆盖快捷标签和手动搜索两种场景，选中即自动填入实时价

**工程优化**

- 新增 `.gitattributes`，强制 Vue/JS/Python 等源码文件行尾符为 LF，从根本上解决 Windows/Linux 混用导致 `npm run build` 报 Invalid end tag 的问题
- 新增 `.editorconfig`，统一团队编辑器缩进与行尾符配置
- `.gitignore` 补充忽略 `frontend/vite.config.js.timestamp-*` 临时文件

---

## v1.3 · 2026-06-12

**Bug 修复**

- 修复交易记录与持仓/现金不联动的问题：提交交易后，持仓明细和可用现金现在会自动同步更新（买入新增/加仓、卖出减仓/清仓，现金同步扣减或增加）
- 修复信号卡片涨跌幅长期显示 0.00% 的问题：页面加载后自动拉取实时行情补全涨跌幅，生成器的 `pct_chg` 计算逻辑也同步修正（之前对单行数据做 `pct_change()` 结果为 NaN）
- 修复前端 Vue SFC 文件行尾符混用导致 Windows 端 `npm run build` 报 Invalid end tag 的问题

**体验优化**

- 持仓页「新增持仓」按钮改为「📥 导入初始持仓」，语义更清晰：该功能仅用于导入平台使用前的已有仓位，不扣减现金余额；日常买卖统一通过「新增交易」完成
- 导入弹窗增加蓝色提示说明，避免与「新增交易」混淆

**工程清理**

- 删除根目录废弃的 `signals/` 目录（旧版单文件信号路径遗留）
- 删除 16 个 Vite 开发服务器临时 timestamp 文件
- 删除根目录废弃的 `portfolio.json`（旧版单用户持仓文件）
- 删除废弃的 `templates/index.html`（已迁移为 Vue SPA）
- 删除重复的小写 `suiy_transactions.json`（正确文件为 `Suiy_transactions.json`）
- 清理 `static/dist/assets/` 下历次构建残留的旧 JS/CSS 产物

---

## v1.2 · 2026-06-10

**新功能**

- **信号快速交易**：信号卡片新增「买入记录」快捷按钮，可直接从信号页面发起交易，自动填入 ETF 代码和实时价格
- **模拟盘胜率追踪**：新增模拟盘标签页，自动以 T+1 开盘价入场、T+N+1 开盘价出场，统计历史信号的胜率、平均收益和持有天数分布
- **实时价格拉取**：交易弹窗选中 ETF 后自动拉取新浪行情实时价，无实时数据时回退到昨收价，来源有明显标注
- **手动触发信号生成**：管理员可在信号看板直接点击「立即生成」强制刷新当日信号，无需等待定时任务，生成进度实时展示

**优化**

- 入金弹窗新增入金后余额预览
- 信号卡片持仓状态展示优化（成本价、浮盈浮亏、仓位占比）
- 系统状态页面新增信号生成任务状态展示

---

## v1.1 · 2026-06-08

**数据源迁移**

- 历史行情数据源最终确定为 **Tushare Pro**（经历了 yfinance → akshare → baostock → tushare 的评估过程，tushare 数据质量和稳定性最佳）
- 信号生成器统一使用 Tushare `pro_bar` 接口拉取 ETF 复权日线数据

**Bug 修复**

- 修复信号文件路径错误（旧路径 `signals/` vs 正确路径 `quant/signals/`）
- 修复推送邮件中 NaN/None 值导致序列化报错的问题
- 修复 `load_users()` 传入多余字段导致 `User` dataclass 初始化失败的问题
- 修复黑名单 ETF 过滤逻辑

---

## v1.0 · 2026-06-06

**首次发布**

**核心功能**

- **多用户持仓管理**：支持多账户独立持仓、各自设定单只/板块仓位上限，管理员可新增/删除账户、重置密码
- **ETF 量化信号**：基于 XGBoost 模型，综合 RSI、MACD、布林带、EMA 金叉、量比、20 日动量等技术指标，每日收盘后自动生成做多候选池
- **持仓感知建议**：信号结合个人持仓状态，自动生成 OPEN（开仓）/ ADD（加仓）/ HOLD（观望）/ REDUCE（减仓）/ SKIP（跳过）五类个性化建议，含止盈止损线判断
- **历史信号档案**：完整保留每日信号记录，支持按日期回溯查看历史推荐
- **回测结果展示**：展示模型在历史数据上的分方向胜率、平均收益等统计
- **每日邮件推送**：收盘后自动向各用户发送个性化信号推送邮件
- **定时任务调度**：Windows 任务计划程序集成，支持每日、每周、每月定时运行

**技术栈**

- 后端：Python + Flask，RESTful API
- 前端：Vue 3 + Vite + Tailwind CSS，单页应用
- 模型：XGBoost 分类器 + 概率校准
- 行情数据：Tushare Pro API
- 实时行情：新浪财经 hq_str 接口
