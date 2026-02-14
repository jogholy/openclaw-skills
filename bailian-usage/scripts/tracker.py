#!/usr/bin/env python3
"""
百炼（DashScope）API 用量记账工具
记录和统计 API 调用的 token 使用量和费用
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
import fcntl
from pathlib import Path

# 百炼公开价格表（¥/千tokens）
PRICING = {
    "text-embedding-v3": {"input": 0.0007, "output": 0},
    "qwen-turbo": {"input": 0.0003, "output": 0.0006},
    "qwen-plus": {"input": 0.0008, "output": 0.002},
    "qwen-max": {"input": 0.002, "output": 0.006},
    "qwen3-max-2026-01-23": {"input": 0.002, "output": 0.006},
    "wanx-v1": {"per_image": 0.04},  # 通义万相按张计费
    # Gemini（免费 tier，记录调用量但不计费）
    "gemini-2.5-flash": {"input": 0, "output": 0},
    "gemini-2.5-pro": {"input": 0, "output": 0},
    # Groq Whisper（免费 tier，按次记录）
    "whisper-large-v3-turbo": {"input": 0, "output": 0},
}

# 中国时区 UTC+8
CHINA_TZ = timezone(timedelta(hours=8))

def get_script_dir():
    """获取脚本所在目录"""
    return Path(__file__).parent.parent

def get_data_dir():
    """获取数据目录，不存在则创建"""
    data_dir = get_script_dir() / "data"
    data_dir.mkdir(exist_ok=True)
    return data_dir

def calculate_cost(model, input_tokens, output_tokens):
    """计算费用"""
    if model not in PRICING:
        return 0.0
    
    pricing = PRICING[model]
    
    # 通义万相按张计费
    if "per_image" in pricing:
        return pricing["per_image"]
    
    # 其他模型按 token 计费
    input_cost = (input_tokens / 1000) * pricing["input"]
    output_cost = (output_tokens / 1000) * pricing["output"]
    return round(input_cost + output_cost, 6)

def get_month_file(date):
    """获取指定日期的月度文件路径"""
    data_dir = get_data_dir()
    return data_dir / f"usage_{date.strftime('%Y-%m')}.json"

def read_usage_file(file_path):
    """安全读取用量文件"""
    if not file_path.exists():
        return []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_SH)
            content = f.read().strip()
            if not content:
                return []
            return json.loads(content)
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def write_usage_file(file_path, data):
    """安全写入用量文件"""
    with open(file_path, 'w', encoding='utf-8') as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        json.dump(data, f, ensure_ascii=False, indent=2)

def record_usage(model, input_tokens, output_tokens, source):
    """记录一条 API 调用"""
    now = datetime.now(CHINA_TZ)
    cost = calculate_cost(model, input_tokens, output_tokens)
    
    record = {
        "timestamp": now.strftime("%Y-%m-%dT%H:%M:%S"),
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "source": source,
        "cost_yuan": cost
    }
    
    file_path = get_month_file(now)
    data = read_usage_file(file_path)
    data.append(record)
    write_usage_file(file_path, data)
    
    print(f"记录成功: {model} | {input_tokens}+{output_tokens} tokens | ¥{cost:.6f}")

def get_day_summary(target_date):
    """获取指定日期的用量汇总"""
    file_path = get_month_file(target_date)
    data = read_usage_file(file_path)
    
    target_str = target_date.strftime("%Y-%m-%d")
    day_records = [r for r in data if r["timestamp"].startswith(target_str)]
    
    if not day_records:
        return {}
    
    # 按模型分组统计
    summary = {}
    for record in day_records:
        model = record["model"]
        if model not in summary:
            summary[model] = {
                "calls": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cost_yuan": 0.0
            }
        
        summary[model]["calls"] += 1
        summary[model]["input_tokens"] += record["input_tokens"]
        summary[model]["output_tokens"] += record["output_tokens"]
        summary[model]["cost_yuan"] += record["cost_yuan"]
    
    # 计算总计
    total = {
        "calls": sum(s["calls"] for s in summary.values()),
        "input_tokens": sum(s["input_tokens"] for s in summary.values()),
        "output_tokens": sum(s["output_tokens"] for s in summary.values()),
        "cost_yuan": sum(s["cost_yuan"] for s in summary.values())
    }
    
    return {
        "date": target_str,
        "models": summary,
        "total": total
    }

def get_summary_days(days):
    """获取最近 N 天的每日汇总"""
    now = datetime.now(CHINA_TZ)
    summaries = []
    
    for i in range(days):
        target_date = now - timedelta(days=i)
        day_summary = get_day_summary(target_date)
        if day_summary:
            summaries.append(day_summary)
    
    # 计算合计
    if summaries:
        total_calls = sum(s["total"]["calls"] for s in summaries)
        total_input = sum(s["total"]["input_tokens"] for s in summaries)
        total_output = sum(s["total"]["output_tokens"] for s in summaries)
        total_cost = sum(s["total"]["cost_yuan"] for s in summaries)
        
        return {
            "period": f"最近{days}天",
            "days": list(reversed(summaries)),  # 按时间正序
            "grand_total": {
                "calls": total_calls,
                "input_tokens": total_input,
                "output_tokens": total_output,
                "cost_yuan": round(total_cost, 6)
            }
        }
    
    return {"period": f"最近{days}天", "days": [], "grand_total": {}}

def get_month_summary():
    """获取本月汇总"""
    now = datetime.now(CHINA_TZ)
    file_path = get_month_file(now)
    data = read_usage_file(file_path)
    
    month_str = now.strftime("%Y-%m")
    month_records = [r for r in data if r["timestamp"].startswith(month_str)]
    
    if not month_records:
        return {"month": month_str, "models": {}, "total": {}}
    
    # 按模型分组统计
    summary = {}
    for record in month_records:
        model = record["model"]
        if model not in summary:
            summary[model] = {
                "calls": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cost_yuan": 0.0
            }
        
        summary[model]["calls"] += 1
        summary[model]["input_tokens"] += record["input_tokens"]
        summary[model]["output_tokens"] += record["output_tokens"]
        summary[model]["cost_yuan"] += record["cost_yuan"]
    
    # 计算总计
    total = {
        "calls": sum(s["calls"] for s in summary.values()),
        "input_tokens": sum(s["input_tokens"] for s in summary.values()),
        "output_tokens": sum(s["output_tokens"] for s in summary.values()),
        "cost_yuan": round(sum(s["cost_yuan"] for s in summary.values()), 6)
    }
    
    return {
        "month": month_str,
        "models": summary,
        "total": total
    }

def main():
    parser = argparse.ArgumentParser(description="百炼 API 用量记账工具")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # record 命令
    record_parser = subparsers.add_parser("record", help="记录 API 调用")
    record_parser.add_argument("--model", required=True, help="模型名称")
    record_parser.add_argument("--input-tokens", type=int, required=True, help="输入 token 数")
    record_parser.add_argument("--output-tokens", type=int, required=True, help="输出 token 数")
    record_parser.add_argument("--source", required=True, help="调用来源")
    
    # today 命令
    subparsers.add_parser("today", help="今天的用量汇总")
    
    # yesterday 命令
    subparsers.add_parser("yesterday", help="昨天的用量汇总")
    
    # summary 命令
    summary_parser = subparsers.add_parser("summary", help="最近 N 天汇总")
    summary_parser.add_argument("--days", type=int, default=7, help="天数（默认7天）")
    
    # month 命令
    subparsers.add_parser("month", help="本月汇总")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == "record":
            record_usage(args.model, args.input_tokens, args.output_tokens, args.source)
        
        elif args.command == "today":
            today = datetime.now(CHINA_TZ)
            summary = get_day_summary(today)
            print(json.dumps(summary, ensure_ascii=False, indent=2))
        
        elif args.command == "yesterday":
            yesterday = datetime.now(CHINA_TZ) - timedelta(days=1)
            summary = get_day_summary(yesterday)
            print(json.dumps(summary, ensure_ascii=False, indent=2))
        
        elif args.command == "summary":
            summary = get_summary_days(args.days)
            print(json.dumps(summary, ensure_ascii=False, indent=2))
        
        elif args.command == "month":
            summary = get_month_summary()
            print(json.dumps(summary, ensure_ascii=False, indent=2))
    
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()