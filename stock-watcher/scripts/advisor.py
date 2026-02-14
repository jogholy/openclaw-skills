#!/usr/bin/env python3
"""
综合投资建议 - 汇总技术面 + 情绪面，LLM 给出投资决策
输出: 操作建议、仓位比例、止盈止损位、风险评级

用法:
  python3 advisor.py --code 300098 --name 高新兴          # 输出 prompt（给 OpenClaw 用）
  python3 advisor.py --code 300098 --name 高新兴 --json   # 输出原始数据
  python3 advisor.py --all                                # 分析所有自选股
  python3 advisor.py --decide                             # 收集数据 + LLM 直接出决策
  python3 advisor.py --decide --all                       # 所有自选股 + LLM 决策

LLM 降级链路: Gemini 2.5 Pro (免费) → Qwen (百炼)
"""
import argparse
import json
import os
import sys
import urllib.request
import urllib.parse
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(__file__))
from config import DATA_DIR, WATCHLIST_FILE, PORTFOLIO_FILE
from technical import analyze as technical_analyze
from sentiment import get_sentiment
from summarize_performance import fetch_realtime_quotes
from market_state import detect_market_state

CST = timezone(timedelta(hours=8))
PROXY = os.environ.get("HTTPS_PROXY", "http://127.0.0.1:7897")
GEMINI_MODELS = ["gemini-3-pro-preview", "gemini-2.5-pro"]
QWEN_MODEL = "qwen-plus"
CLAUDE_MODELS = ["claude-opus-4-20250514", "claude-sonnet-4-20250514"]
CLAUDE_BASE_URL = "https://code.newcli.com/claude/aws/v1/messages"


def _get_claude_key():
    config_path = os.path.expanduser("~/.openclaw/openclaw.json")
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            cfg = json.load(f)
        try:
            return cfg["models"]["providers"]["generic"]["apiKey"]
        except (KeyError, TypeError):
            pass
    return os.environ.get("ANTHROPIC_API_KEY", "")


def _call_claude(prompt, max_tokens=4096):
    """调用 Claude API（走代理），自动尝试: Opus → Sonnet"""
    import requests as _req
    api_key = _get_claude_key()
    if not api_key:
        return None, "未找到 Claude API Key"

    proxies = {"https": PROXY, "http": PROXY}
    last_err = None

    for model in CLAUDE_MODELS:
        try:
            resp = _req.post(
                CLAUDE_BASE_URL,
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                },
                json={
                    "model": model,
                    "max_tokens": max_tokens,
                    "messages": [{"role": "user", "content": prompt}],
                },
                proxies=proxies,
                timeout=120,
            )
            if resp.status_code == 200:
                text = resp.json()["content"][0]["text"].strip()
                return text, model
            else:
                last_err = f"HTTP {resp.status_code}: {resp.text[:100]}"
                print(f"  Claude {model} 失败: {last_err}", file=sys.stderr)
        except Exception as e:
            last_err = str(e)
            print(f"  Claude {model} 失败: {last_err}", file=sys.stderr)
            continue

    return None, last_err


def _get_gemini_key():
    config_path = os.path.expanduser("~/.openclaw/openclaw.json")
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            cfg = json.load(f)
        try:
            return cfg["skills"]["entries"]["nano-banana-pro"]["apiKey"]
        except (KeyError, TypeError):
            pass
    return os.environ.get("GOOGLE_API_KEY", "")


def _get_dashscope_key():
    config_path = os.path.expanduser("~/.openclaw/openclaw.json")
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            cfg = json.load(f)
        try:
            return cfg["models"]["providers"]["bailian"]["apiKey"]
        except (KeyError, TypeError):
            pass
    return os.environ.get("DASHSCOPE_API_KEY", "")


def _call_gemini(prompt, max_tokens=4096):
    """调用 Gemini（走代理），自动尝试多个模型：3 Pro → 2.5 Pro"""
    api_key = _get_gemini_key()
    if not api_key:
        return None, "未找到 Gemini API Key"

    proxy_handler = urllib.request.ProxyHandler({"https": PROXY, "http": PROXY})
    opener = urllib.request.build_opener(proxy_handler)
    last_err = None

    for model in GEMINI_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        body = json.dumps({
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.3},
        }).encode('utf-8')

        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        try:
            with opener.open(req, timeout=60) as resp:
                result = json.loads(resp.read().decode('utf-8'))
            text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
            return text, model
        except Exception as e:
            last_err = str(e)
            print(f"  Gemini {model} 失败: {last_err}", file=sys.stderr)
            continue

    return None, last_err


def _call_qwen(prompt, max_tokens=4096):
    """调用 Qwen（百炼 DashScope），国内直连"""
    api_key = _get_dashscope_key()
    if not api_key:
        return None, "未找到 DashScope API Key"

    url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    body = json.dumps({
        "model": QWEN_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.3,
    }).encode('utf-8')

    req = urllib.request.Request(url, data=body, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    })

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode('utf-8'))
        text = result["choices"][0]["message"]["content"].strip()
        return text, None
    except Exception as e:
        return None, str(e)


def call_llm(prompt, max_tokens=4096):
    """LLM 降级链路: Claude Opus → Sonnet → Gemini 3 Pro → 2.5 Pro → Qwen"""
    # 1. 尝试 Claude（Opus → Sonnet）
    print("  尝试 Claude (Opus → Sonnet)...", file=sys.stderr)
    text, model_or_err = _call_claude(prompt, max_tokens)
    if text:
        return text, model_or_err

    print(f"  Claude 全部失败，尝试 Gemini...", file=sys.stderr)

    # 2. 尝试 Gemini（3 Pro → 2.5 Pro）
    text, model_or_err2 = _call_gemini(prompt, max_tokens)
    if text:
        return text, model_or_err2

    print(f"  Gemini 全部失败，降级到 Qwen...", file=sys.stderr)

    # 3. 降级 Qwen
    text, err = _call_qwen(prompt, max_tokens)
    if text:
        return text, "qwen-plus"

    return None, f"所有 LLM 均失败。Claude: {model_or_err}, Gemini: {model_or_err2}, Qwen: {err}"


def _read_json(path, default=None):
    if not os.path.exists(path):
        return default if default is not None else {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return default if default is not None else {}


def _load_watchlist():
    if not os.path.exists(WATCHLIST_FILE):
        return []
    with open(WATCHLIST_FILE, 'r', encoding='utf-8') as f:
        lines = [l.strip() for l in f if l.strip()]
    return [(p[0], p[1]) for line in lines if len(p := line.split('|')) == 2]


def _load_portfolio():
    return _read_json(PORTFOLIO_FILE, {})


def gather_data(code, name):
    """收集一只股票的所有分析数据"""
    data = {"code": code, "name": name}

    # 1. 技术面分析
    try:
        tech = technical_analyze(code)
        if "error" not in tech:
            data["technical"] = {
                "close": tech["close"],
                "indicators": tech["indicators"],
                "signals": tech.get("signals", []),
            }
        else:
            data["technical"] = {"error": tech["error"]}
    except Exception as e:
        data["technical"] = {"error": str(e)}

    # 2. 实时行情
    try:
        quotes = fetch_realtime_quotes([(code, name)])
        q = quotes.get(code)
        if q:
            data["realtime"] = {
                "price": q["price"],
                "change_pct": q["change_pct"],
                "volume": q.get("volume", 0),
                "turnover": q.get("turnover", 0),
            }
    except Exception as e:
        data["realtime"] = {"error": str(e)}

    # 3. 情绪面分析 (Gemini)
    try:
        sentiment = get_sentiment(code, name)
        data["sentiment"] = {
            "score": sentiment.get("score", 0),
            "label": sentiment.get("label", "unknown"),
            "summary": sentiment.get("summary", ""),
            "key_events": sentiment.get("key_events", []),
            "news_count": sentiment.get("news_count", 0),
        }
    except Exception as e:
        data["sentiment"] = {"error": str(e)}

    # 4. 持仓信息
    portfolio = _load_portfolio()
    pos = portfolio.get("positions", {}).get(code)
    if pos:
        data["position"] = {
            "shares": pos["shares"],
            "avg_cost": pos["avg_cost"],
            "total_cost": pos["total_cost"],
        }
    data["portfolio_cash"] = portfolio.get("total_cash", 0)
    data["portfolio_total"] = portfolio.get("initial_capital", 0)

    return data


def format_advisor_prompt(stock_data_list, market=None):
    """构建给 Opus 的 prompt"""
    now = datetime.now(CST).strftime("%Y-%m-%d %H:%M")

    prompt = f"""你是一位经验丰富的A股投资顾问。当前时间: {now}

请基于以下数据，为每只股票给出综合投资建议。

要求:
1. 综合技术面和情绪面，给出明确的操作建议
2. 建议必须具体可执行（具体价位、仓位比例）
3. 分三个风险偏好给建议（保守/平衡/激进）
4. 必须给出止盈止损位
5. 评估当前持仓的合理性

"""

    # 市场状态
    if market and "error" not in market:
        prompt += f"## 大盘环境\n"
        prompt += f"市场状态: {market.get('label', 'unknown')} (评分 {market.get('score', 0)})\n"
        sh = market.get("shanghai", {})
        prompt += f"上证: {sh.get('price', 'N/A')} ({'+' if sh.get('change_pct', 0) >= 0 else ''}{sh.get('change_pct', 0):.2f}%)\n"
        sz = market.get("shenzhen", {})
        if sz:
            prompt += f"深证: {sz.get('price', 'N/A')} ({'+' if sz.get('change_pct', 0) >= 0 else ''}{sz.get('change_pct', 0):.2f}%)\n"
        br = market.get("breadth", {})
        if br and br.get("up"):
            prompt += f"涨跌比: {br['up']}↑ / {br['down']}↓ (比值 {br.get('ratio', 0)})\n"
        prompt += "\n"

    for data in stock_data_list:
        prompt += f"\n{'='*50}\n"
        prompt += f"## {data['name']}({data['code']})\n\n"

        # 实时行情
        rt = data.get("realtime", {})
        if "error" not in rt:
            prompt += f"现价: ¥{rt.get('price', 'N/A')} ({'+' if rt.get('change_pct', 0) >= 0 else ''}{rt.get('change_pct', 0):.2f}%)\n"

        # 技术面
        tech = data.get("technical", {})
        if "error" not in tech:
            ind = tech.get("indicators", {})
            signals = tech.get("signals", [])
            prompt += f"\n技术面:\n"
            prompt += f"  昨收: {tech.get('close', 'N/A')}\n"
            prompt += f"  MA5: {ind.get('ma5', 'N/A')} | MA10: {ind.get('ma10', 'N/A')} | MA20: {ind.get('ma20', 'N/A')}\n"
            macd = ind.get("macd", )
            prompt += f"  MACD: DIF={macd.get('dif', 'N/A')} DEA={macd.get('dea', 'N/A')} 柱={macd.get('hist', 'N/A')}\n"
            kdj = ind.get("kdj", {})
            prompt += f"  KDJ: K={kdj.get('k', 'N/A'):.1f} D={kdj.get('d', 'N/A'):.1f} J={kdj.get('j', 'N/A'):.1f}\n"
            prompt += f"  RSI6: {ind.get('rsi6', 'N/A')} | RSI12: {ind.get('rsi12', 'N/A')}\n"
            boll = ind.get("boll", {})
            prompt += f"  布林: 上={boll.get('upper', 'N/A')} 中={boll.get('mid', 'N/A')} 下={boll.get('lower', 'N/A')}\n"
            if signals:
                prompt += f"  信号: {', '.join(s['name'] + '(' + s['type'] + ',' + str(s['strength']) + '/10)' for s in signals)}\n"

        # 情绪面
        sent = data.get("sentiment", {})
        if "error" not in sent:
            prompt += f"\n情绪面:\n"
            prompt += f"  评分: {sent.get('score', 0)}/10 ({sent.get('label', 'unknown')})\n"
            prompt += f"  摘要: {sent.get('summary', '')}\n"
            events = sent.get("key_events", [])
            if events:
                prompt += f"  关键事件: {'; '.join(events)}\n"

        # 持仓
        pos = data.get("position")
        if pos:
            current_price = rt.get("price", tech.get("close", 0))
            pnl_pct = ((current_price - pos["avg_cost"]) / pos["avg_cost"] * 100) if pos["avg_cost"] else 0
            prompt += f"\n持仓:\n"
            prompt += f"  {pos['shares']}股 | 成本 ¥{pos['avg_cost']:.3f} | 浮盈 {'+' if pnl_pct >= 0 else ''}{pnl_pct:.2f}%\n"
        else:
            prompt += f"\n未持仓\n"

        prompt += f"可用资金: ¥{data.get('portfolio_cash', 0):,.2f}\n"

    prompt += f"""
{'='*50}

请为每只股票输出以下格式的建议:

### [股票名称]
**综合评级**: 强烈买入 / 买入 / 持有 / 减仓 / 卖出 / 强烈卖出
**信心指数**: 1-10

**操作建议**:
- 保守型: [具体操作 + 仓位比例]
- 平衡型: [具体操作 + 仓位比例]
- 激进型: [具体操作 + 仓位比例]

**关键价位**:
- 止损位: ¥xx.xx (理由)
- 止盈位1: ¥xx.xx (理由)
- 止盈位2: ¥xx.xx (理由)
- 支撑位: ¥xx.xx
- 压力位: ¥xx.xx

**风险提示**: [主要风险因素]
**逻辑概述**: [2-3句话总结投资逻辑]
"""

    return prompt


def main():
    parser = argparse.ArgumentParser(description="综合投资建议")
    parser.add_argument("--code", help="股票代码")
    parser.add_argument("--name", help="股票名称")
    parser.add_argument("--all", action="store_true", help="分析所有自选股")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--decide", action="store_true",
                        help="收集数据 + 生成决策 prompt（由 OpenClaw Opus 处理）")
    args = parser.parse_args()

    stocks = []
    if args.all:
        stocks = _load_watchlist()
    elif args.code and args.name:
        stocks = [(args.code, args.name)]
    else:
        # 默认只分析持仓股
        portfolio = _load_portfolio()
        positions = portfolio.get("positions", {})
        if positions:
            for code, pos in positions.items():
                stocks.append((code, pos["name"]))
        else:
            print("请指定 --code/--name 或 --all")
            return

    if not stocks:
        print("无股票可分析")
        return

    # 收集数据
    print("📊 正在收集数据...", file=sys.stderr)

    # 市场状态
    print("  检测市场状态...", file=sys.stderr)
    market = detect_market_state()

    all_data = []
    for code, name in stocks:
        print(f"  分析 {name}({code})...", file=sys.stderr)
        data = gather_data(code, name)
        all_data.append(data)

    if args.json:
        # JSON 模式只输出收集到的数据，不调用 LLM
        output = {"market": market, "stocks": all_data}
        print(json.dumps(output, ensure_ascii=False, indent=2))
    elif args.decide:
        # 决策模式：收集数据 + Claude Opus 做投资决策
        prompt = format_advisor_prompt(all_data, market)
        print("🤖 正在生成投资建议...", file=sys.stderr)
        result, model_used = call_llm(prompt, max_tokens=4096)
        if result:
            print(f"📊 投资建议（模型: {model_used}）\n")
            print(result)
        else:
            print(f"❌ LLM 决策失败: {model_used}", file=sys.stderr)
            # 降级输出 prompt，让调用者自行处理
            print(prompt)
    else:
        # 默认模式：只输出 prompt
        prompt = format_advisor_prompt(all_data, market)
        print(prompt)


if __name__ == "__main__":
    main()
