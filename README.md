# OpenClaw Skills

A collection of custom skills for [OpenClaw](https://openclaw.ai).

## Skills

### 📱 xhs-publisher
小红书自动化发布工具。基于 Playwright 浏览器自动化，支持扫码登录、自动发布图文笔记、AI 智能配图。

- 8种文案风格（默认/测评/教程/日常/清单/故事/辩论/对比）
- 风格权重自适应系统
- AI配图（Gemini优先，Qwen备选）
- See [xhs-publisher/SKILL.md](xhs-publisher/SKILL.md)

### 📈 stock-watcher
A股股票盯盘助手。支持自选股管理、行情查询、技术指标分析、交易信号监控、盘前提要/盘后总结。

- 数据来源：10jqka.com.cn（同花顺）
- 交易日判断（基于 akshare）
- 资金仓位管理
- See [stock-watcher/SKILL.md](stock-watcher/SKILL.md)

### 🔧 foxcode
FoxCode Claude API 代理平台管理工具。查询服务器状态、用量统计、额度余额。

- 服务器状态监控（各线路 24h uptime）
- 用量查询（quota/models/trend/records）
- JWT 自动认证
- See [foxcode/SKILL.md](foxcode/SKILL.md)

### 💰 bailian-usage
阿里云百炼平台 API 用量追踪。记录 Qwen、Gemini、Groq Whisper 等模型的调用次数和 token 消耗。

- 本地 SQLite 数据库
- 昨日/今日用量查询
- 费用估算
- See [bailian-usage/SKILL.md](bailian-usage/SKILL.md)

## Installation

每个 skill 目录结构：
```
skill-name/
├── SKILL.md          # 技能文档
├── scripts/          # 脚本
├── config.json       # 配置（如需要）
└── data/             # 数据文件（如需要）
```

安装到 OpenClaw：
```bash
cp -r skill-name ~/.openclaw/skills/
```

## Requirements

- OpenClaw 2026.2.1+
- Python 3.8+
- 各 skill 的依赖见其 SKILL.md

## License

MIT

## Author

Evan (@jogholy)
