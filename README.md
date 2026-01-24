# Prediction Market Tracker

自动追踪和分析预测市场的交易数据，支持 Kalshi 和 Polymarket。

## 功能

### Kalshi Tracker
- 📊 每日自动下载 Kalshi 交易数据
- 📈 生成 7 天滚动总交易量图表
- 🏈 按市场类型（NFL、NCAA、NBA、MLB、加密货币等）分类分析
- 🔄 GitHub Actions 自动化运行
- 📧 定期邮件报告通知

### Polymarket Tracker
- 📊 每周自动抓取符合条件的 Polymarket 市场
- 🎯 筛选条件：交易量 > $1M，概率 95-99% 或 1-5%，6 个月内结束
- 📥 生成 Excel 报告，托管在 GitHub Pages
- 💬 Lark/飞书自动通知

## 快速开始

### 本地运行

```bash
# 克隆仓库
git clone https://github.com/WYIN711/Prediction-Market.git
cd Prediction-Market

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements-analysis.txt

# 下载最新数据
python scripts/download_kalshi_trades.py

# 生成报告
./analysis/update_plots.sh
```

### GitHub Actions 自动化

项目包含两个自动化工作流：

1. **Daily Data Download** (`download-data.yml`)
   - 每天 09:30 UTC (05:30 ET) 运行
   - 从 Kalshi API 下载最新交易数据
   - 压缩后上传到 GitHub Releases

2. **Weekly Reports** (`generate-reports.yml`)
   - 每周一和周四 13:00 UTC (08:00 ET) 运行
   - 下载最近 90 天数据
   - 生成分析图表和 CSV
   - 上传报告为 Artifacts
   - 发送邮件通知

## 设置 GitHub Actions

### 1. 启用 Workflow Permissions

在 GitHub 仓库设置中：
- Settings → Actions → General → Workflow permissions
- 选择 "Read and write permissions"

### 2. 配置邮件通知（可选）

如需邮件通知，在 Repository Secrets 中添加：

| Secret | 说明 |
|--------|------|
| `MAIL_USERNAME` | 发送邮件的 Gmail 地址 |
| `MAIL_PASSWORD` | Gmail 应用专用密码（非登录密码） |
| `MAIL_TO` | 接收报告的邮箱地址 |

获取 Gmail 应用专用密码：
1. 启用两步验证：Google Account → Security → 2-Step Verification
2. 创建应用密码：Google Account → Security → App passwords

### 3. 上传历史数据

如果你有本地历史数据（`data/kalshi_trades/*.json`），运行：

```bash
# 安装 GitHub CLI
brew install gh

# 登录 GitHub
gh auth login

# 上传历史数据到 Releases
./scripts/upload_historical_data.sh
```

## 数据存储

由于交易数据文件较大（每天 200MB-800MB），数据存储在 GitHub Releases 而非 Git 仓库中：

- 每个交易日创建一个 Release（如 `data-2025-12-28`）
- 数据以 `.tar.gz` 压缩格式存储
- GitHub Actions 自动下载所需数据生成报告

### 下载历史数据

```bash
# 使用 gh CLI 下载特定日期
gh release download data-2025-12-28 -D data/kalshi_trades
cd data/kalshi_trades && tar -xzf kalshi_trades_2025-12-28.tar.gz
```

## Polymarket Tracker

### 功能说明

Polymarket Tracker 每周六上午 10:00（香港时间）自动运行，查找符合以下条件的市场：
- 交易量超过 100 万美元
- 概率在 95%-99% 或 1%-5% 之间（即高概率或低概率事件）
- 事件在未来 6 个月内结束

### 设置 Lark 通知

在 Repository Secrets 中添加：

| Secret | 说明 |
|--------|------|
| `LARK_WEBHOOK_URL` | Lark/飞书 Bot 的 Webhook URL |

### 访问报告

报告托管在 GitHub Pages：
- URL: `https://wyin711.github.io/Prediction-Market/polymarket/`

### 手动触发

在 GitHub Actions 页面选择 "Polymarket Weekly Fetch" 工作流，点击 "Run workflow"。

---

## 项目结构

```
.
├── .github/workflows/      # GitHub Actions 工作流
│   ├── download-data.yml   # Kalshi 每日数据下载
│   ├── generate-reports.yml# Kalshi 定期报告生成
│   └── polymarket-weekly.yml # Polymarket 每周抓取
├── analysis/
│   ├── generate_all_plots.py  # 主分析脚本
│   ├── update_plots.sh        # 报告生成入口
│   ├── compute_volume.py      # 交易量计算
│   ├── market_type_trends.py  # 市场类型分析
│   └── runs/                  # 报告输出目录
├── data/
│   └── kalshi_trades/         # 交易数据 JSON 文件
├── scripts/
│   ├── download_kalshi_trades.py  # Kalshi 数据下载脚本
│   ├── send_lark_notification.py  # Kalshi Lark 通知
│   └── upload_historical_data.sh  # 历史数据上传
├── polymarket/                # Polymarket Tracker
│   ├── fetch_markets.py       # 市场抓取脚本
│   ├── send_lark_notification.py # Lark 通知
│   ├── requirements.txt       # Python 依赖
│   └── docs/                  # GitHub Pages 报告
├── requirements-analysis.txt  # Kalshi 分析依赖
└── README.md
```

## 报告输出

每次运行生成以下文件：

| 文件 | 说明 |
|------|------|
| `7d_rolling_total_volume.png` | 7 天滚动总交易量图 |
| `top_10_market_types_7d_ma.png` | Top 10 市场类型 7 天均量趋势图 |
| `daily_total_volume_python.csv` | 每日总交易量数据 |
| `daily_category_volume.csv` | 按类别的每日交易量数据 |

## 市场分类

交易数据按以下类别分类：

- **NFL Football** - NFL 比赛
- **NCAA Football** - NCAA 大学橄榄球
- **NBA Basketball** - NBA 篮球
- **MLB Baseball** - MLB 棒球
- **NHL Hockey** - NHL 冰球
- **Soccer** - 足球（英超、欧冠等）
- **Tennis** - 网球
- **Cryptocurrency** - 加密货币
- **Politics/Elections** - 政治/选举
- **Other** - 其他

## License

MIT
