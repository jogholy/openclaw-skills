#!/usr/bin/env python3
"""
新闻情绪分析 - 抓取个股相关新闻并用 Gemini 做情绪打分
输出: sentiment_score (-10 ~ +10), summary, key_events

用法:
  python3 sentiment.py --code 300098 --name 高新兴
  python3 sentiment.py --code 300098 --name 高新兴 --json
"""
import argparse
import json
import os
import re
import sys
import urllib.request
import urllib.parse
from datetime import datetime, timedelta, timezone

CST = timezone(timedelta(hours=8))

# Gemini API (免费层，走代理)
PROXY = os.environ.get("HTTPS_PROXY", "http://127.0.0.1:7897")
GEMINI_MODEL = "gemini-2.5-flash"


def _get_gemini_key():
    """从 openclaw 配置读取 Gemini API key"""
    config_path = os.path.expanduser("~/.openclaw/openclaw.json")
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            cfg = json.load(f)
        # 尝试从 skills.entries.nano-banana-pro.apiKey 读取
        try:
            return cfg["skills"]["entries"]["nano-banana-pro"]["apiKey"]
        except (KeyError, TypeError):
            pass
    return os.environ.get("GOOGLE_API_KEY", "")


def fetch_news_10jqka(code, name, limit=10):
    """从同花顺抓取个股新闻"""
    news_list = []
    try:
        url = f"https://search.10jqka.com.cn/gateway/s?q={urllib.parse.quote(name)}&type=news&page=1&perpage={limit}"
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.10jqka.com.cn/",
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))

        items = data.get("data", {}).get("list", [])
        for item in items[:limit]:
            news_list.append({
                "title": item.get("title", "").replace("<em>", "").replace("</em>", ""),
                "summary": item.get("digest", "")[:200],
                "time": item.get("datetime", ""),
                "source": item.get("source", ""),
            })
    except Exception as e:
        sys.stderr.write(f"同花顺新闻抓取失败: {e}\n")

    return news_list


def fetch_news_eastmoney(code, name, limit=10):
    """从东方财富抓取个股新闻"""
    news_list = []
    try:
        url = f"https://search-api-web.eastmoney.com/search/jsonp?cb=jQuery&param=%7B%22uid%22%3A%22%22%2C%22keyword%22%3A%22{urllib.parse.quote(name)}%22%2C%22type%22%3A%5B%22cmsArticleWebOld%22%5D%2C%22client%22%3A%22web%22%2C%22clientType%22%3A%22web%22%2C%22clientVersion%22%3A%22curr%22%2C%22param%22%3A%7B%22cmsArticleWebOld%22%3A%7B%22searchScope%22%3A%22default%22%2C%22sort%22%3A%22default%22%2C%22pageIndex%22%3A1%2C%22pageSize%22%3A{limit}%7D%7D%7D"
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://so.eastmoney.com/",
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode('utf-8')
        # 去掉 JSONP 包装
        json_str = raw[raw.index('(') + 1:raw.rindex(')')]
        data = json.loads(json_str)
        # 东方财富返回的是列表，不是 dict
        items = data.get("result", {}).get("cmsArticleWebOld", [])
        if isinstance(items, dict):
            items = items.get("list", [])
        for item in items[:limit]:
            news_list.append({
                "title": re.sub(r'<[^>]+>', '', item.get("title", "")),
                "summary": re.sub(r'<[^>]+>', '', item.get("content", ""))[:200],
                "time": item.get("date", ""),
                "source": item.get("mediaName", ""),
            })
    except Exception as e:
        sys.stderr.write(f"东方财富新闻抓取失败: {e}\n")

    return news_list


def analyze_sentiment_gemini(news_list, code, name):
    """用 Gemini 分析新闻情绪"""
    api_key = _get_gemini_key()
    if not api_key:
        return {"error": "未找到 Gemini API Key"}

    if not news_list:
        return {
            "score": 0,
            "label": "neutral",
            "summary": "未找到相关新闻",
            "key_events": [],
        }

    news_text = "\n".join(
        f"- [{n['time']}] {n['title']}: {n['summary']}"
        for n in news_list
    )

    # 精简 prompt，减少新闻内容只保留标题
    news_text = "\n".join(
        f"- [{n['time']}] {n['title']}"
        for n in news_list
    )

    prompt = f"""分析以下 {name}({code}) 的近期新闻情绪，输出JSON: {{"score":-10到10整数,"label":"bearish/neutral/bullish","summary":"50字以内","key_events":["事件1","事件2"]}}

{news_text}"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={api_key}"

    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 2048,
            "responseMimeType": "application/json",
        },
    }).encode('utf-8')

    # 设置代理
    proxy_handler = urllib.request.ProxyHandler({
        "https": PROXY,
        "http": PROXY,
    })
    opener = urllib.request.build_opener(proxy_handler)

    req = urllib.request.Request(url, data=body, headers={
        "Content-Type": "application/json",
    })

    try:
        with opener.open(req, timeout=30) as resp:
            result = json.loads(resp.read().decode('utf-8'))

        text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
        return json.loads(text)
    except Exception as e:
        sys.stderr.write(f"Gemini 情绪分析失败: {e}\n")
        return {"error": str(e)}


def get_sentiment(code, name):
    """获取个股情绪分析结果"""
    # 先试同花顺，失败用东方财富
    news = fetch_news_10jqka(code, name)
    if not news:
        news = fetch_news_eastmoney(code, name)

    sentiment = analyze_sentiment_gemini(news, code, name)
    sentiment["news_count"] = len(news)
    sentiment["news"] = news[:5]  # 保留前5条
    return sentiment


def main():
    parser = argparse.ArgumentParser(description="新闻情绪分析")
    parser.add_argument("--code", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = get_sentiment(args.code, args.name)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if "error" in result:
            print(f"❌ 分析失败: {result['error']}")
        else:
            score = result.get("score", 0)
            icon = "🟢" if score > 2 else "🔴" if score < -2 else "⚪"
            print(f"{icon} {args.name}({args.code}) 情绪评分: {score}/10 ({result.get('label', 'unknown')})")
            print(f"  {result.get('summary', '')}")
            events = result.get("key_events", [])
            if events:
                print(f"  关键事件:")
                for e in events:
                    print(f"    • {e}")


if __name__ == "__main__":
    main()
