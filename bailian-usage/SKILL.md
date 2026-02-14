# bailian-usage

百炼（DashScope）API 用量记账和统计工具

## 描述

这个 skill 用于记录和统计百炼 API 的使用情况，包括 token 消耗和费用计算。支持按日、按月统计，方便成本控制和用量分析。

## 功能特性

- 记录每次 API 调用的详细信息（模型、tokens、来源、费用）
- 按月分文件存储，便于管理
- 支持多种统计维度：今日、昨日、最近N天、本月
- 内置百炼公开价格表，自动计算费用
- 并发安全的文件操作
- 纯 Python 标准库实现，无外部依赖

## 使用方式

### 记录 API 调用

```bash
# 记录一次文本生成调用
python3 scripts/tracker.py record --model qwen-turbo --input-tokens 100 --output-tokens 200 --source content_gen

# 记录一次 embedding 调用
python3 scripts/tracker.py record --model text-embedding-v3 --input-tokens 500 --output-tokens 0 --source embedding

# 记录图片生成调用
python3 scripts/tracker.py record --model wanx-v1 --input-tokens 0 --output-tokens 1 --source image_gen
```

### 查看统计信息

```bash
# 今天的用量汇总
python3 scripts/tracker.py today

# 昨天的用量汇总
python3 scripts/tracker.py yesterday

# 最近7天汇总（默认）
python3 scripts/tracker.py summary

# 最近30天汇总
python3 scripts/tracker.py summary --days 30

# 本月汇总
python3 scripts/tracker.py month
```

### 输出格式示例

```json
{
  "date": "2026-02-13",
  "models": {
    "qwen-turbo": {
      "calls": 5,
      "input_tokens": 1200,
      "output_tokens": 800,
      "cost_yuan": 0.0012
    },
    "text-embedding-v3": {
      "calls": 10,
      "input_tokens": 5000,
      "output_tokens": 0,
      "cost_yuan": 0.0035
    }
  },
  "total": {
    "calls": 15,
    "input_tokens": 6200,
    "output_tokens": 800,
    "cost_yuan": 0.0047
  }
}
```

## 数据文件位置

- 数据目录：`/home/admin/.openclaw/skills/bailian-usage/data/`
- 文件格式：`usage_YYYY-MM.json`（按月分文件）
- 每条记录包含：timestamp, model, input_tokens, output_tokens, source, cost_yuan

## 在其他脚本中使用

### 方法1：subprocess 调用

```python
import subprocess
import json

# 记录调用
subprocess.run([
    "python3", "/home/admin/.openclaw/skills/bailian-usage/scripts/tracker.py",
    "record", "--model", "qwen-turbo", 
    "--input-tokens", "100", "--output-tokens", "200", 
    "--source", "my_script"
])

# 获取今日统计
result = subprocess.run([
    "python3", "/home/admin/.openclaw/skills/bailian-usage/scripts/tracker.py", "today"
], capture_output=True, text=True)
today_stats = json.loads(result.stdout)
```

### 方法2：直接 import

```python
import sys
sys.path.append('/home/admin/.openclaw/skills/bailian-usage/scripts')
from tracker import record_usage, get_day_summary
from datetime import datetime, timezone, timedelta

# 记录调用
record_usage("qwen-turbo", 100, 200, "my_script")

# 获取今日统计
china_tz = timezone(timedelta(hours=8))
today = datetime.now(china_tz)
stats = get_day_summary(today)
```

## 支持的模型和价格

当前支持的模型及价格（¥/千tokens）：

- `text-embedding-v3`: 输入 0.0007，输出 0
- `qwen-turbo`: 输入 0.0003，输出 0.0006
- `qwen-plus`: 输入 0.0008，输出 0.002
- `qwen-max`: 输入 0.002，输出 0.006
- `qwen3-max-2026-01-23`: 输入 0.002，输出 0.006
- `wanx-v1`: 按张计费 0.04¥/张

未知模型按 0 费用计算，不会报错。

## 常用 source 标识

建议使用的调用来源标识：

- `content_gen`: 内容生成
- `comments`: 评论回复
- `embedding`: 向量化
- `image_gen`: 图片生成
- `translation`: 翻译
- `summarization`: 摘要
- `chat`: 对话
- `analysis`: 分析

## 注意事项

- 所有时间使用 Asia/Shanghai 时区（UTC+8）
- 数据文件使用文件锁确保并发安全
- 费用计算精确到小数点后6位
- data/ 目录会自动创建