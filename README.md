# ETF Quant 量化交易系统

> 基于机器学习的 A 股 ETF 多空信号生成与持仓管理平台

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![Vue](https://img.shields.io/badge/Vue-3.x-42b883.svg)](https://vuejs.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 简介 / Overview

**中文**

ETF Quant 是一套面向个人投资者的量化交易辅助系统，利用 XGBoost 模型对 A 股主流 ETF 进行次日涨跌概率预测，自动生成买入候选信号，并通过邮件推送给多位用户。系统配备完整的 Web 管理界面，支持多用户持仓管理、交易记录（与现金余额自动联动）、历史信号回溯、模拟盘胜率追踪和模型参数调整。

**English**

ETF Quant is a quantitative trading assistant for individual investors in the A-share market. It uses an XGBoost model to predict next-day up/down probabilities for major ETFs, automatically generates buy-candidate signals, and pushes daily reports via email to multiple users. A full-featured web dashboard supports multi-user portfolio management, trade logging (with automatic cash sync), historical signal review, paper-trading win-rate tracking, and model parameter tuning.

---

## 核心功能 / Features

| 功能 | 说明 |
|------|------|
| 📈 信号生成 | 每日收盘后，基于技术指标特征预测次日涨跌概率，筛选候选池；管理员可手动触发 |
| 🔔 邮件推送 | 自动发送个性化日报（含持仓感知建议 OPEN/ADD/HOLD/REDUCE），支持多用户 |
| 📊 持仓管理 | 多账户独立持仓与现金；买卖交易后持仓和现金余额自动同步；支持导入初始持仓 |
| 🎰 模拟盘追踪 | 以 T+1 开盘价入场，自动统计历史信号胜率、平均收益与持有天数分布 |
| ⚡ 快速交易 | 信号卡片直接发起买入，自动填入 ETF 代码和实时价格 |
| 🎯 模型调参 | 在线调整概率门槛、ETF 黑名单，无需重启服务 |
| 📉 回测验证 | 历史回测模块，评估策略在不同周期的表现 |
| 🔐 权限管理 | 管理员 / 普通用户两级权限，Session 认证 |

---

## 技术栈 / Tech Stack

**后端 Backend**
- Python 3.11+
- Flask（Web 服务 + REST API）· gunicorn（生产部署）
- XGBoost（机器学习模型）
- Tushare Pro（历史行情数据源）· 新浪财经 hq_str（实时行情）
- Pandas / NumPy / scikit-learn

**前端 Frontend**
- Vue 3 (Composition API + `<script setup>`)
- Vite + Tailwind CSS
- Chart.js（K 线图、技术指标、成交量、RSI）

**调度 Scheduler**
- Windows 任务计划程序（Task Scheduler）/ Linux cron

**工程规范**
- `.gitattributes`：前端源码统一 LF 行尾符，避免跨平台构建异常
- `.editorconfig`：编辑器缩进与行尾符统一配置

---

## 项目结构 / Project Structure

```
AI_PROJECT/
├── config.py                  # 🔒 敏感配置（不入库，见 config.example.py）
├── config.example.py          # 配置模板
├── web_app.py                 # Flask 主服务 + 所有 API
├── run_daily.py               # 每日 15:35 收盘任务（周一至五）
├── run_weekly.py              # 每周日任务：重训 + 生成周一信号
├── requirements.txt
├── CHANGELOG.md
│
├── quant/
│   ├── data/
│   │   ├── fetch_historical.py    # 历史行情拉取（Tushare Pro）
│   │   └── historical/            # Parquet 格式历史数据（.gitignore）
│   ├── features/
│   │   └── engineer.py            # 技术指标特征工程
│   ├── models/
│   │   ├── trainer.py             # 模型训练（XGBoost）
│   │   └── saved/                 # 训练好的模型文件（.gitignore）
│   ├── signals/
│   │   ├── generator.py           # 信号候选池生成
│   │   ├── notifier.py            # 邮件格式化与发送
│   │   ├── model_config.json      # 模型参数持久化（概率门槛、黑名单）
│   │   ├── candidates.json        # 当日候选池（.gitignore）
│   │   └── history/               # 每日信号历史档案（.gitignore）
│   └── utils/
│       └── etf_list.py            # ETF 代码与名称映射表
│
├── portfolios/                    # 用户持仓 JSON（.gitignore）
├── static/dist/                   # 前端构建产物（Flask 托管）
│
└── frontend/                      # Vue 3 SPA 源码
    └── src/views/
        ├── LoginView.vue
        ├── SignalView.vue          # 今日信号 + 历史回溯 + 模拟盘
        ├── PortfolioView.vue       # 持仓管理 + 交易记录
        ├── ModelView.vue           # 模型参数调整（管理员）
        └── SystemView.vue          # 系统状态（管理员）
```

---

## 快速开始 / Quick Start

### 1. 克隆仓库

```bash
git clone https://github.com/your-username/etf-quant.git
cd etf-quant
```

### 2. 安装 Python 依赖

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
pip install flask optuna
```

### 3. 填写配置

```bash
copy config.example.py config.py   # Windows
# 编辑 config.py，填入邮箱授权码等信息
```

### 4. 拉取历史数据

```bash
python -m quant.data.fetch_historical
```

### 5. 训练初始模型

```bash
python run_weekly.py
```

### 6. 构建前端

```bash
cd frontend
npm install
npm run build
cd ..
```

### 7. 启动 Web 服务

```bash
python web_app.py
```

访问 `http://localhost:5000`，默认管理员账号在 `portfolios/users.json` 中配置。

### 8. 配置定时任务（Windows）

在 Windows 任务计划程序中创建任务，每个交易日 15:35 后运行 `run_daily.py`，每周日运行 `run_weekly.py`。

---

## 本地开发 / Local Development

### 启动后端

```powershell
cd D:\AI_PROJECT
.venv\Scripts\activate
python web_app.py
# 访问 http://localhost:5000
```

### 启动前端（开发模式，热更新）

```powershell
cd D:\AI_PROJECT\frontend
npm run dev
# 访问 http://localhost:5173
```

> 生产模式使用 `npm run build` 构建产物，由 Flask 直接托管，无需单独启动前端。

### 通过 ngrok 暴露本地服务（外网访问）

```powershell
# 安装 ngrok：https://ngrok.com/download
# 启动后端后，在新终端运行：
ngrok http 5000
# ngrok 会输出公网地址，如 https://xxxx.ngrok-free.app
```

---

## 服务器部署 / Server Deployment

### 连接服务器（SSH 配置）

在本地 `~/.ssh/config` 中添加：

```
Host jump
    HostName proxy.limengxun.com
    Port 2222
    User <your_username>

Host etf
    HostName <container_ip>
    Port <container_ssh_port>
    User root
    ProxyJump jump
```

然后直接运行：

```powershell
ssh etf
```

### 服务器端启动后端

```bash
cd /workspace/<username>/etf
# 使用 gunicorn 生产模式启动
pip install gunicorn --break-system-packages
gunicorn -w 2 -b 0.0.0.0:8000 web_app:app --daemon --log-file logs/gunicorn.log
# 访问 http://<container_ip>:<mapped_port>
```

停止服务：

```bash
pkill gunicorn
```

### 服务器端构建前端

前端构建产物由 Flask/Gunicorn 直接托管，在服务器上构建一次即可：

```bash
cd /workspace/<username>/etf/frontend
npm install
npm run build
cd ..
```

### 服务器端配置 cron 定时任务

```bash
crontab -e
```

添加以下内容：

```
# 周一至五收盘信号生成
35 15 * * 1-5 cd /workspace/<username>/etf && python run_daily.py
# 周日重训 + 周一预报
0  10 * * 0   cd /workspace/<username>/etf && python run_weekly.py
```

---

## 定时任务调度 / Scheduled Tasks

| 任务 | 触发时间 | 脚本 | 说明 |
|------|----------|------|------|
| Quant_Daily  | 周一至五 15:35 | `run_daily.py` | 收盘信号生成 + 推送 |
| Quant_Weekly | 周日 10:00     | `run_weekly.py` | 重训 + 周一信号预报 |

---

## 数据流 / Data Flow

```
Tushare Pro 行情数据
    │
    ▼
历史 Parquet 文件（增量更新）
    │
    ▼
特征工程（RSI/MACD/布林带/量比等）─→ XGBoost 训练 ─→ 模型文件(.pkl)
                                                │
                                                ▼
                                        信号候选池生成（概率门槛过滤）
                                                │
                              ┌─────────────────┴──────────────────┐
                              ▼                                      ▼
                    持仓感知建议（per-user）               新浪实时行情补全涨跌幅
                              │
                              ▼
                     邮件推送 + Web Dashboard
```

---

## 免责声明 / Disclaimer

本项目仅供学习和研究使用，不构成任何投资建议。量化模型存在失效风险，历史表现不代表未来收益。投资有风险，入市需谨慎。

*This project is for educational and research purposes only and does not constitute investment advice. Quantitative models may fail; past performance does not guarantee future results.*

---

## License

MIT © 2026
