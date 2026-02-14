#!/usr/bin/env python3
"""
市场状态检测 - 判断当前大盘处于牛市/震荡/熊市
基于上证指数 + 成交量 + 涨跌比

用法:
  python3 market_state.py
  python3 market_state.py --json
"""
import argparse
import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(__file__))

CST = timezone(timedelta(hours=8))


def fetch_index_data(index_code="sh000001"):
    """获取大盘指数数据（上证指数）"""
    try:
        url = f"https://qt.gtimg.cn/q={index_code}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode('gbk')

        parts = raw.split('~')
        if len(parts) < 45:
            return None

        return {
            "name": parts[1],
            "price": float(parts[3]),
            "change": float(parts[31]),
            "change_pct": float(parts[32]),
            "volume": float(parts[36]),  # 成交量（手）
            "turnover": float(parts[37]),  # 成交额（万元）
            "high": float(parts[33]),
            "low": float(parts[34]),
            "open": float(parts[5]),
            "prev_close": float(parts[4]),
        }
    except Exception as e:
        sys.stderr.write(f"获取指数数据失败: {e}\n")
        return None


def fetch_market_breadth():
    """获取涨跌家数（市场宽度）"""
    try:
        # 沪深涨跌家数
        url = "https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=1&po=1&np=1&fltt=2&invt=2&fid=f3&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23&fields=f3"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))

        total = data.get("data", {}).get("total", 0)

        # 上涨家数
        url_up = "https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=1&po=1&np=1&fltt=2&invt=2&fid=f3&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23&fields=f3&fid=f3&pz=1&po=1"
        # 简化：用东方财富大盘统计接口
        url_stats = "https://push2ex.eastmoney.com/getTopicZDFenBu?ut=7eea3edcaed734bea9cb3fddcbbc315d&dession=&mession=&fc=1"
        req2 = urllib.request.Request(url_stats, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req2, timeout=10) as resp:
            stats = json.loads(resp.read().decode('utf-8'))

        fenbu = stats.get("data", {}).get("fenbu", [])
        up_count = 0
        down_count = 0
        flat_count = 0
        for item in fenbu:
            pct = item.get("x", 0)
            count = item.get("y", 0)
            if pct > 0:
                up_count += count
            elif pct < 0:
                down_count += count
            else:
                flat_count += count

        return {
            "up": up_count,
            "down": down_count,
            "flat": flat_count,
            "total": up_count + down_count + flat_count,
            "ratio": round(up_count / max(down_count, 1), 2),
        }
    except Exception as e:
        sys.stderr.write(f"获取涨跌家数失败: {e}\n")
        return None


def detect_market_state():
    """综合判断市场状态"""
    index = fetch_index_data("sh000001")  # 上证
    index_sz = fetch_index_data("sz399001")  # 深证
    breadth = fetch_market_breadth()

    if not index:
        return {"state": "unknown", "error": "无法获取指数数据"}

    result = {
        "timestamp": datetime.now(CST).isoformat(),
        "shanghai": {
            "price": index["price"],
            "change_pct": index["change_pct"],
            "volume": index["volume"],
            "turnover": index["turnover"],
        },
    }

    if index_sz:
        result["shenzhen"] = {
            "price": index_sz["price"],
            "change_pct": index_sz["change_pct"],
        }

    if breadth:
        result["breadth"] = breadth

    # 综合判断
    score = 0  # -10 极度恐慌, +10 极度贪婪

    # 1. 指数涨跌 (权重 40%)
    pct = index["change_pct"]
    if pct > 2:
        score += 4
    elif pct > 1:
        score += 3
    elif pct > 0.5:
        score += 2
    elif pct > 0:
        score += 1
    elif pct > -0.5:
        score -= 1
    elif pct > -1:
        score -= 2
    elif pct > -2:
        score -= 3
    else:
        score -= 4

    # 2. 涨跌比 (权重 40%)
    if breadth:
        ratio = breadth["ratio"]
        if ratio > 3:
            score += 4
        elif ratio > 2:
            score += 3
        elif ratio > 1.5:
            score += 2
        elif ratio > 1:
            score += 1
        elif ratio > 0.7:
            score -= 1
        elif ratio > 0.5:
            score -= 2
        elif ratio > 0.3:
            score -= 3
        else:
            score -= 4

    # 3. 深证联动 (权重 20%)
    if index_sz:
        sz_pct = index_sz["change_pct"]
        if sz_pct > 1:
            score += 2
        elif sz_pct > 0:
            score += 1
        elif sz_pct > -1:
            score -= 1
        else:
            score -= 2

    # 状态判定
    if score >= 6:
        state = "strong_bull"
        label = "强势上涨"
        emoji = "🚀"
    elif score >= 3:
        state = "bull"
        label = "偏多"
        emoji = "🟢"
    elif score >= -2:
        state = "neutral"
        label = "震荡"
        emoji = "⚪"
    elif score >= -5:
        state = "bear"
        label = "偏空"
        emoji = "🔴"
    else:
        state = "strong_bear"
        label = "强势下跌"
        emoji = "💀"

    result["state"] = state
    result["label"] = label
    result["emoji"] = emoji
    result["score"] = score

    return result


def format_report(result):
    """格式化市场状态报告"""
    if "error" in result:
        return f"❌ {result['error']}"

    lines = []
    lines.append(f"{result['emoji']} 市场状态: {result['label']} (评分 {result['score']})")

    sh = result.get("shanghai", {})
    lines.append(f"  上证: {sh.get('price', 'N/A')} ({'+' if sh.get('change_pct', 0) >= 0 else ''}{sh.get('change_pct', 0):.2f}%)")

    sz = result.get("shenzhen", {})
    if sz:
        lines.append(f"  深证: {sz.get('price', 'N/A')} ({'+' if sz.get('change_pct', 0) >= 0 else ''}{sz.get('change_pct', 0):.2f}%)")

    br = result.get("breadth", {})
    if br:
        lines.append(f"  涨跌比: {br.get('up', 0)}↑ / {br.get('down', 0)}↓ (比值 {br.get('ratio', 0)})")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="市场状态检测")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = detect_market_state()

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_report(result))


if __name__ == "__main__":
    main()
