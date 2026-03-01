#!/usr/bin/env python3
"""
轨道交通情报监控脚本
自动获取当前月份和上个月份的最新信息，并生成内容总结
"""

import os
import sys
import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

def get_month_keywords():
    """获取当前月份和上个月份的关键词"""
    now = datetime.now()
    current_month = now.strftime("%Y年%m月")
    last_month = (now.replace(day=1) - timedelta(days=1)).strftime("%Y年%m月")
    return current_month, last_month

def search_with_serper(query, api_key):
    """使用 Serper API 搜索"""
    web_search_plus = Path(__file__).parent.parent.parent / "web-search-plus" / "scripts" / "search.py"
    
    if not web_search_plus.exists():
        print(f"❌ web-search-plus 未找到: {web_search_plus}")
        return []
    
    try:
        result = subprocess.run(
            ["python3", str(web_search_plus), "--query", query, "--max-results", "5"],
            capture_output=True,
            text=True,
            timeout=30,
            env={**os.environ, "SERPER_API_KEY": api_key}
        )
        
        if result.returncode != 0:
            print(f"❌ 搜索失败: {result.stderr}")
            return []
        
        data = json.loads(result.stdout)
        return data.get("results", [])
    
    except Exception as e:
        print(f"❌ 搜索出错: {e}")
        return []

def summarize_with_ai(results, topic_name):
    """使用 AI 对搜索结果做总结，优先 Qwen Max，失败则用 Claude Sonnet"""
    if not results:
        return "未找到相关信息"
    
    # 构建提示词
    content = f"请总结以下关于'{topic_name}'的最新信息（2026年2-3月）：\n\n"
    for i, item in enumerate(results, 1):
        title = item.get("title", "")
        snippet = item.get("snippet", "")
        date = item.get("date", "")
        content += f"{i}. {title}\n"
        if date:
            content += f"   日期: {date}\n"
        if snippet:
            content += f"   内容: {snippet}\n"
        content += "\n"
    
    content += "\n请用中文总结以上信息的要点，包括：\n"
    content += "1. 主要事件和动态\n"
    content += "2. 关键数据和时间节点\n"
    content += "3. 重要趋势和影响\n"
    content += "\n总结要简洁明了，突出重点。"
    
    # 先尝试 Qwen Max
    summary = try_qwen_max(content)
    if summary:
        return summary
    
    # Qwen Max 失败，尝试 Claude Sonnet
    print("⚠️ Qwen Max 失败，尝试使用 Claude Sonnet...")
    summary = try_claude_sonnet(content)
    if summary:
        return summary
    
    # 都失败了，返回简单格式
    print("⚠️ AI 总结失败，使用简单格式")
    return format_simple_summary(results)

def try_qwen_max(content):
    """尝试使用 Qwen Max (DashScope) 生成总结"""
    try:
        import requests
        
        # 从 OpenClaw 配置读取 API Key
        config_path = Path.home() / ".openclaw" / "openclaw.json"
        api_key = None
        
        if config_path.exists():
            with open(config_path) as f:
                config = json.load(f)
                api_key = config.get("models", {}).get("providers", {}).get("bailian", {}).get("apiKey")
        
        if not api_key:
            return None
        
        # DashScope API 端点
        api_url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
        
        response = requests.post(
            api_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "qwen-max-2025-01-25",
                "messages": [
                    {"role": "user", "content": content}
                ],
                "temperature": 0.7
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            summary = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return summary if summary else None
        else:
            print(f"   Qwen Max API 返回错误: {response.status_code}")
            return None
    
    except Exception as e:
        print(f"   Qwen Max 调用失败: {e}")
        return None

def try_claude_sonnet(content):
    """尝试使用 Claude Sonnet 生成总结"""
    try:
        import requests
        
        # 从 OpenClaw 配置读取 API Key
        config_path = Path.home() / ".openclaw" / "openclaw.json"
        api_key = None
        base_url = None
        
        if config_path.exists():
            with open(config_path) as f:
                config = json.load(f)
                generic_config = config.get("models", {}).get("providers", {}).get("generic", {})
                api_key = generic_config.get("apiKey")
                base_url = generic_config.get("baseUrl")
        
        if not api_key or not base_url:
            return None
        
        # Claude API 端点
        api_url = f"{base_url}/v1/messages"
        
        response = requests.post(
            api_url,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 2000,
                "messages": [
                    {"role": "user", "content": content}
                ]
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            summary = data.get("content", [{}])[0].get("text", "")
            return summary if summary else None
        else:
            print(f"   Claude Sonnet API 返回错误: {response.status_code}")
            return None
    
    except Exception as e:
        print(f"   Claude Sonnet 调用失败: {e}")
        return None

def format_simple_summary(results):
    """简单格式化搜索结果"""
    summary = ""
    for i, item in enumerate(results, 1):
        title = item.get("title", "")
        snippet = item.get("snippet", "")
        date = item.get("date", "")
        url = item.get("url", "")
        
        summary += f"\n{i}. **{title}**\n"
        if date:
            summary += f"   📅 {date}\n"
        if snippet:
            summary += f"   📝 {snippet}\n"
        if url:
            summary += f"   🔗 {url}\n"
    
    return summary

def send_to_telegram(summaries, search_period):
    """发送总结到 Telegram"""
    try:
        # 构建消息
        message = f"📊 **轨道交通情报日报**\n\n"
        message += f"📅 时间范围: {search_period}\n"
        message += f"⏰ 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        message += "=" * 40 + "\n\n"
        
        for item in summaries:
            topic = item["topic"]
            summary = item["summary"]
            results_count = item["results_count"]
            
            message += f"## {topic}\n\n"
            message += f"📈 找到 {results_count} 条最新信息\n\n"
            message += summary + "\n\n"
            message += "=" * 40 + "\n\n"
        
        # 使用 OpenClaw 的 message 工具发送
        # 由于消息可能很长，需要分段发送
        max_length = 4000  # Telegram 消息长度限制
        
        if len(message) <= max_length:
            # 直接发送
            import subprocess
            result = subprocess.run(
                ["openclaw", "message", "send", "--channel", "telegram", "--target", "8500612003", "--message", message],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                print("✅ 已发送到 Telegram")
            else:
                print(f"⚠️ Telegram 发送失败: {result.stderr}")
        else:
            # 分段发送
            parts = []
            current_part = ""
            
            for line in message.split("\n"):
                if len(current_part) + len(line) + 1 > max_length:
                    parts.append(current_part)
                    current_part = line + "\n"
                else:
                    current_part += line + "\n"
            
            if current_part:
                parts.append(current_part)
            
            # 发送每一段
            for i, part in enumerate(parts, 1):
                import subprocess
                result = subprocess.run(
                    ["openclaw", "message", "send", "--channel", "telegram", "--target", "8500612003", "--message", part],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode == 0:
                    print(f"✅ 已发送第 {i}/{len(parts)} 段到 Telegram")
                else:
                    print(f"⚠️ 第 {i} 段发送失败: {result.stderr}")
                
                # 避免发送过快
                if i < len(parts):
                    import time
                    time.sleep(1)
        
        return True
    
    except Exception as e:
        print(f"⚠️ Telegram 发送失败: {e}")
        return False

def main():
    """主函数"""
    # 获取月份关键词
    current_month, last_month = get_month_keywords()
    print(f"📅 搜索时间范围: {last_month} 和 {current_month}\n")
    
    # 获取 API Key
    api_key = os.environ.get("SERPER_API_KEY", "02b48b7cc39da01d6a3c6b6bb259f961e1e5333f")
    
    # 定义监控主题
    topics = [
        {
            "name": "轨道交通最新动态",
            "query": f"轨道交通 {current_month} {last_month}"
        },
        {
            "name": "轨道车辆最新消息",
            "query": f"轨道车辆 地铁车辆 动车组 {current_month} {last_month}"
        },
        {
            "name": "大型养路机械最新消息",
            "query": f"大型养路机械 大机 铁路养护 {current_month} {last_month}"
        },
        {
            "name": "地铁工程车最新消息",
            "query": f"地铁工程车 轨道工程车 {current_month} {last_month}"
        }
    ]
    
    # 搜索并总结每个主题
    all_summaries = []
    
    for topic in topics:
        print(f"\n{'='*60}")
        print(f"🔍 正在搜索: {topic['name']}")
        print(f"{'='*60}\n")
        
        # 搜索
        results = search_with_serper(topic["query"], api_key)
        
        if not results:
            print(f"⚠️ 未找到相关信息\n")
            continue
        
        print(f"✅ 找到 {len(results)} 条结果\n")
        
        # 生成总结
        print("📝 正在生成总结...\n")
        summary = summarize_with_ai(results, topic["name"])
        
        # 输出总结
        print(f"## {topic['name']}\n")
        print(summary)
        print("\n")
        
        all_summaries.append({
            "topic": topic["name"],
            "query": topic["query"],
            "results_count": len(results),
            "summary": summary,
            "results": results
        })
    
    # 保存结果
    output_file = Path(__file__).parent.parent / ".data" / "rail_monitor_latest.json"
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "search_period": f"{last_month} - {current_month}",
            "summaries": all_summaries
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 监控完成！结果已保存到: {output_file}")
    
    # 发送到 Telegram
    if all_summaries:
        print("\n📤 正在发送到 Telegram...")
        send_to_telegram(all_summaries, f"{last_month} - {current_month}")

if __name__ == "__main__":
    main()
