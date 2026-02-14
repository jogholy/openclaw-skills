---
name: stock-watcher
description: Manage and monitor a personal stock watchlist with support for adding, removing, listing stocks, and summarizing their recent performance using data from 10jqka.com.cn. Use when the user wants to track specific stocks, get performance summaries, or manage their watchlist.
---

# Stock Watcher Skill

股票自选股管理 + 资金仓位 + 技术分析 + 信号监控 + 投资建议

## 数据源
- 实时行情：腾讯行情 API (qt.gtimg.cn)
- 日K线/技术指标：同花顺 (d.10jqka.com.cn)
- 新闻情绪：东方财富搜索 API + Gemini 情绪分析
- 大盘指数：腾讯行情 + 东方财富

## 架构分层

| 层级 | 模型 | 用途 |
|------|------|------|
| 数据采集 | 脚本直算 | 技术指标、行情、市场状态 |
| 情绪分析 | Gemini (免费) | 新闻抓取 + 情绪打分 |
| 投资建议 | Opus 4.6 | 综合决策、仓位、止盈止损 |
| 定时调度 | Sonnet | cron 任务执行 |

## 脚本一览

| 脚本 | 功能 | 优先级 |
|------|------|--------|
| `summarize_performance.py` | 自选股实时行情 | P0 |
| `portfolio.py` | 资金仓位管理 | P0 |
| `technical.py` | 技术指标 + 信号检测 | P0 |
| `ocr_reader.py` | OCR读取券商截图 | P0 |
| `monitor.py` | 信号监控（定时扫描 + 价格提醒） | P1 |
| `price_alert.py` | 价格提醒管理 | P1 |
| `daily_report.py` | 盘前提要 / 盘后总结 | P1 |
| `sentiment.py` | 新闻情绪分析 (Gemini) | P2 |
| `market_state.py` | 大盘市场状态检测 | P2 |
| `advisor.py` | 综合投资建议（数据收集 + Claude Opus 决策） | P2 |
| `backtest.py` | 信号回测验证 | P2 |
| `add_stock.py` | 添加自选股 | P0 |
| `remove_stock.py` | 删除自选股 | P0 |
| `list_stocks.py` | 列出自选股 | P0 |
| `clear_watchlist.py` | 清空自选股 | P0 |

## 用法

### 行情查看
```bash
python3 scripts/summarize_performance.py          # 自选股行情
python3 scripts/summarize_performance.py --json    # JSON 格式
```

### 资金仓位
```bash
python3 scripts/portfolio.py init --capital 100000
python3 scripts/portfolio.py deposit --amount 50000
python3 scripts/portfolio.py withdraw --amount 10000
python3 scripts/portfolio.py buy --code 600053 --name 九鼎投资 --shares 1000 --price 18.85
python3 scripts/portfolio.py sell --code 600053 --shares 500 --price 20.00
python3 scripts/portfolio.py status                # 账户概览
python3 scripts/portfolio.py trades                # 交易流水
```

### 技术分析
```bash
python3 scripts/technical.py 600053          # 技术指标 + 信号
python3 scripts/technical.py 600053 --json   # JSON 格式
```

### 信号监控 (P1)
```bash
python3 scripts/monitor.py                   # 扫描所有自选股信号
python3 scripts/monitor.py --json            # JSON 格式
```

### 价格提醒 (P1)
```bash
python3 scripts/price_alert.py add --code 300098 --name 高新兴 --condition above --price 7.00
python3 scripts/price_alert.py add --code 300098 --name 高新兴 --condition below --price 5.50 --note "止损位"
python3 scripts/price_alert.py list
python3 scripts/price_alert.py remove --index 0
python3 scripts/price_alert.py clear
```

### 盘前提要 / 盘后总结 (P1)
```bash
python3 scripts/daily_report.py morning      # 盘前提要
python3 scripts/daily_report.py evening      # 盘后总结
```

### 新闻情绪分析 (P2)
```bash
HTTPS_PROXY=http://127.0.0.1:7897 python3 scripts/sentiment.py --code 300098 --name 高新兴
HTTPS_PROXY=http://127.0.0.1:7897 python3 scripts/sentiment.py --code 300098 --name 高新兴 --json
```

### 市场状态检测 (P2)
```bash
python3 scripts/market_state.py              # 大盘状态
python3 scripts/market_state.py --json
```

### 综合投资建议 (P2)
```bash
# 收集数据 + Claude Opus 直接出决策（降级: Opus → Sonnet → Gemini 3 Pro → 2.5 Pro → Qwen）
HTTPS_PROXY=http://127.0.0.1:7897 python3 scripts/advisor.py --decide
HTTPS_PROXY=http://127.0.0.1:7897 python3 scripts/advisor.py --decide --all
# 只输出数据（不调 LLM）
HTTPS_PROXY=http://127.0.0.1:7897 python3 scripts/advisor.py --json
# 只输出 prompt（给 OpenClaw 手动处理）
HTTPS_PROXY=http://127.0.0.1:7897 python3 scripts/advisor.py --code 300098 --name 高新兴
```

### 信号回测 (P2)
```bash
python3 scripts/backtest.py 300098                    # 回测单只股票
python3 scripts/backtest.py 300098 --json             # JSON 输出
python3 scripts/backtest.py --all                     # 回测所有自选股
python3 scripts/backtest.py 300098 --signal "MACD金叉" # 只看特定信号
```

### OCR 读图
```bash
python3 scripts/ocr_reader.py /path/to/screenshot.jpg
python3 scripts/ocr_reader.py /path/to/screenshot.jpg --json
```

### 自选股管理
```bash
python3 scripts/add_stock.py 600053 九鼎投资
python3 scripts/remove_stock.py 600053
python3 scripts/list_stocks.py
python3 scripts/clear_watchlist.py
```

## 定时任务

| 时间 | 任务 | 频率 |
|------|------|------|
| 9:15 | 盘前提要 | 工作日 |
| 10:00, 11:00 | 信号监控(上午) | 工作日 |
| 13:30, 14:30 | 信号监控(下午) | 工作日 |
| 15:15 | 盘后总结 | 工作日 |

## 信号检测

自动检测以下买卖信号（强度 1-10）：
- MA 金叉/死叉（5/10、5/20）
- MACD 金叉/死叉
- KDJ 低位金叉/高位死叉
- KDJ 超买超卖区
- RSI 超买超卖
- 布林带触轨
- 均线多头/空头排列

## 数据存储

- 自选股：`~/.clawdbot/stock_watcher/watchlist.txt`
- 账户数据：`~/.clawdbot/stock_watcher/portfolio.json`
- 交易流水：`~/.clawdbot/stock_watcher/trades.json`
- 价格提醒：`~/.clawdbot/stock_watcher/price_alerts.json`
- 信号历史：`~/.clawdbot/stock_watcher/signal_history.json`
