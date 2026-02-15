#!/usr/bin/env python3
"""
技术指标分析模块
支持：MA、MACD、KDJ、RSI、布林带
数据源：同花顺日线 API
"""
import argparse
import json
import os
import sys
import urllib.request
import re
from datetime import datetime, timedelta, timezone

CST = timezone(timedelta(hours=8))

# ── 数据获取 ──────────────────────────────────────────

def get_market_prefix(code):
    if code.startswith(('6', '5')):
        return 'hs_' + code
    else:
        return 'hs_' + code

def fetch_daily_klines(code, days=250):
    """获取日K线数据（同花顺）"""
    url = f"https://d.10jqka.com.cn/v6/line/hs_{code}/01/last.js"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://stockpage.10jqka.com.cn/',
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        raw = resp.read().decode('utf-8', errors='replace')

    # 解析 JSONP: quotebridge_v6_line_hs_XXXXXX_01_last({...})
    m = re.search(r'\((\{.*\})\)', raw, re.DOTALL)
    if not m:
        raise RuntimeError(f"无法解析K线数据: {code}")

    data = json.loads(m.group(1))
    name = data.get('name', code)
    lines = data.get('data', '').split(';')

    klines = []
    for line in lines[-days:]:
        parts = line.split(',')
        if len(parts) < 6:
            continue
        klines.append({
            'date': parts[0],       # YYYYMMDD
            'open': float(parts[1]),
            'close': float(parts[2]) if parts[2] else float(parts[1]),
            'high': float(parts[3]) if parts[3] else float(parts[1]),
            'low': float(parts[4]) if parts[4] else float(parts[1]),
            'volume': int(parts[5]) if parts[5] else 0,
        })

    # 修正：同花顺格式是 open,high,low,close
    # 实际验证：字段顺序是 date,open,high,low,close,volume,amount,...
    corrected = []
    for line in lines[-days:]:
        parts = line.split(',')
        if len(parts) < 6:
            continue
        corrected.append({
            'date': parts[0],
            'open': float(parts[1]),
            'high': float(parts[2]),
            'low': float(parts[3]),
            'close': float(parts[4]),
            'volume': int(parts[5]),
        })

    return name, corrected

# ── 指标计算 ──────────────────────────────────────────

def calc_ma(closes, period):
    """简单移动平均"""
    if len(closes) < period:
        return [None] * len(closes)
    result = [None] * (period - 1)
    for i in range(period - 1, len(closes)):
        result.append(round(sum(closes[i - period + 1:i + 1]) / period, 4))
    return result

def calc_ema(values, period):
    """指数移动平均"""
    if not values:
        return []
    k = 2 / (period + 1)
    ema = [values[0]]
    for i in range(1, len(values)):
        ema.append(round(ema[-1] * (1 - k) + values[i] * k, 4))
    return ema

def calc_macd(closes, fast=12, slow=26, signal=9):
    """MACD"""
    ema_fast = calc_ema(closes, fast)
    ema_slow = calc_ema(closes, slow)
    dif = [round(f - s, 4) for f, s in zip(ema_fast, ema_slow)]
    dea = calc_ema(dif, signal)
    macd = [round((d - e) * 2, 4) for d, e in zip(dif, dea)]
    return dif, dea, macd

def calc_kdj(klines, n=9, m1=3, m2=3):
    """KDJ"""
    k_vals, d_vals, j_vals = [], [], []
    k, d = 50.0, 50.0
    for i in range(len(klines)):
        start = max(0, i - n + 1)
        highs = [kl['high'] for kl in klines[start:i + 1]]
        lows = [kl['low'] for kl in klines[start:i + 1]]
        hn = max(highs)
        ln = min(lows)
        c = klines[i]['close']
        rsv = ((c - ln) / (hn - ln) * 100) if hn != ln else 50
        k = round((m1 - 1) / m1 * k + 1 / m1 * rsv, 2)
        d = round((m2 - 1) / m2 * d + 1 / m2 * k, 2)
        j = round(3 * k - 2 * d, 2)
        k_vals.append(k)
        d_vals.append(d)
        j_vals.append(j)
    return k_vals, d_vals, j_vals

def calc_rsi(closes, period=14):
    """RSI"""
    if len(closes) < period + 1:
        return [None] * len(closes)
    result = [None] * period
    gains, losses = [], []
    for i in range(1, period + 1):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    rs = avg_gain / avg_loss if avg_loss != 0 else 100
    result.append(round(100 - 100 / (1 + rs), 2))
    for i in range(period + 1, len(closes)):
        diff = closes[i] - closes[i - 1]
        avg_gain = (avg_gain * (period - 1) + max(diff, 0)) / period
        avg_loss = (avg_loss * (period - 1) + max(-diff, 0)) / period
        rs = avg_gain / avg_loss if avg_loss != 0 else 100
        result.append(round(100 - 100 / (1 + rs), 2))
    return result

def calc_boll(closes, period=20, k=2):
    """布林带"""
    mid = calc_ma(closes, period)
    upper, lower = [], []
    for i in range(len(closes)):
        if mid[i] is None:
            upper.append(None)
            lower.append(None)
        else:
            start = max(0, i - period + 1)
            std = (sum((c - mid[i]) ** 2 for c in closes[start:i + 1]) / period) ** 0.5
            upper.append(round(mid[i] + k * std, 4))
            lower.append(round(mid[i] - k * std, 4))
    return mid, upper, lower

# ── 综合分析 ──────────────────────────────────────────

def analyze(code):
    """对单只股票做完整技术分析"""
    name, klines = fetch_daily_klines(code, 250)
    if len(klines) < 30:
        return {"error": f"数据不足（仅 {len(klines)} 天）"}

    closes = [k['close'] for k in klines]
    latest = klines[-1]

    # MA
    ma5 = calc_ma(closes, 5)
    ma10 = calc_ma(closes, 10)
    ma20 = calc_ma(closes, 20)
    ma60 = calc_ma(closes, 60)

    # MACD
    dif, dea, macd_hist = calc_macd(closes)

    # KDJ
    k_vals, d_vals, j_vals = calc_kdj(klines)

    # RSI
    rsi6 = calc_rsi(closes, 6)
    rsi14 = calc_rsi(closes, 14)

    # BOLL
    boll_mid, boll_upper, boll_lower = calc_boll(closes)

    # 最新值
    result = {
        "code": code,
        "name": name,
        "date": latest['date'],
        "close": latest['close'],
        "open": latest['open'],
        "high": latest['high'],
        "low": latest['low'],
        "indicators": {
            "ma5": ma5[-1],
            "ma10": ma10[-1],
            "ma20": ma20[-1],
            "ma60": ma60[-1] if ma60[-1] else None,
            "macd": {"dif": dif[-1], "dea": dea[-1], "hist": macd_hist[-1]},
            "kdj": {"k": k_vals[-1], "d": d_vals[-1], "j": j_vals[-1]},
            "rsi6": rsi6[-1],
            "rsi14": rsi14[-1],
            "boll": {
                "upper": boll_upper[-1],
                "mid": boll_mid[-1],
                "lower": boll_lower[-1],
            },
        },
        "signals": [],
    }

    # ── 信号检测 ──
    signals = []

    # MA 金叉/死叉
    if ma5[-1] and ma10[-1] and ma5[-2] and ma10[-2]:
        if ma5[-2] <= ma10[-2] and ma5[-1] > ma10[-1]:
            signals.append({"type": "buy", "name": "MA5/10金叉", "strength": 6})
        elif ma5[-2] >= ma10[-2] and ma5[-1] < ma10[-1]:
            signals.append({"type": "sell", "name": "MA5/10死叉", "strength": 6})

    if ma5[-1] and ma20[-1] and ma5[-2] and ma20[-2]:
        if ma5[-2] <= ma20[-2] and ma5[-1] > ma20[-1]:
            signals.append({"type": "buy", "name": "MA5/20金叉", "strength": 7})
        elif ma5[-2] >= ma20[-2] and ma5[-1] < ma20[-1]:
            signals.append({"type": "sell", "name": "MA5/20死叉", "strength": 7})

    # MACD 金叉/死叉
    if len(dif) >= 2 and len(dea) >= 2:
        if dif[-2] <= dea[-2] and dif[-1] > dea[-1]:
            signals.append({"type": "buy", "name": "MACD金叉", "strength": 7})
        elif dif[-2] >= dea[-2] and dif[-1] < dea[-1]:
            signals.append({"type": "sell", "name": "MACD死叉", "strength": 7})

    # KDJ 超买超卖
    if k_vals[-1] < 20 and d_vals[-1] < 20:
        signals.append({"type": "buy", "name": "KDJ超卖区", "strength": 5})
    elif k_vals[-1] > 80 and d_vals[-1] > 80:
        signals.append({"type": "sell", "name": "KDJ超买区", "strength": 5})

    # KDJ 金叉/死叉
    if len(k_vals) >= 2 and len(d_vals) >= 2:
        if k_vals[-2] <= d_vals[-2] and k_vals[-1] > d_vals[-1] and k_vals[-1] < 50:
            signals.append({"type": "buy", "name": "KDJ低位金叉", "strength": 7})
        elif k_vals[-2] >= d_vals[-2] and k_vals[-1] < d_vals[-1] and k_vals[-1] > 50:
            signals.append({"type": "sell", "name": "KDJ高位死叉", "strength": 7})

    # RSI 超买超卖
    if rsi6[-1] and rsi6[-1] < 20:
        signals.append({"type": "buy", "name": "RSI6超卖(<20)", "strength": 6})
    elif rsi6[-1] and rsi6[-1] > 80:
        signals.append({"type": "sell", "name": "RSI6超买(>80)", "strength": 6})

    # 布林带
    if boll_lower[-1] and latest['close'] <= boll_lower[-1]:
        signals.append({"type": "buy", "name": "触及布林下轨", "strength": 5})
    elif boll_upper[-1] and latest['close'] >= boll_upper[-1]:
        signals.append({"type": "sell", "name": "触及布林上轨", "strength": 5})

    # 均线多头/空头排列
    if ma5[-1] and ma10[-1] and ma20[-1]:
        if ma5[-1] > ma10[-1] > ma20[-1]:
            signals.append({"type": "buy", "name": "均线多头排列", "strength": 8})
        elif ma5[-1] < ma10[-1] < ma20[-1]:
            signals.append({"type": "sell", "name": "均线空头排列", "strength": 8})

    result["signals"] = signals
    return result

# ── 输出 ──────────────────────────────────────────────

def print_analysis(result):
    if "error" in result:
        print(f"❌ {result['error']}")
        return

    ind = result["indicators"]
    print(f"═══ {result['name']} ({result['code']}) 技术分析 ═══")
    print(f"  日期: {result['date']}  收盘: {result['close']}")
    print()

    # MA
    print(f"  📊 均线")
    print(f"     MA5: {ind['ma5']}  MA10: {ind['ma10']}  MA20: {ind['ma20']}  MA60: {ind['ma60'] or 'N/A'}")

    # MACD
    m = ind['macd']
    print(f"  📈 MACD")
    print(f"     DIF: {m['dif']}  DEA: {m['dea']}  柱: {m['hist']}")

    # KDJ
    k = ind['kdj']
    print(f"  🔄 KDJ")
    print(f"     K: {k['k']}  D: {k['d']}  J: {k['j']}")

    # RSI
    print(f"  💪 RSI")
    print(f"     RSI6: {ind['rsi6']}  RSI14: {ind['rsi14']}")

    # BOLL
    b = ind['boll']
    print(f"  📏 布林带")
    print(f"     上轨: {b['upper']}  中轨: {b['mid']}  下轨: {b['lower']}")

    # 信号
    signals = result.get("signals", [])
    if signals:
        print()
        print(f"  ⚡ 信号")
        for s in sorted(signals, key=lambda x: x['strength'], reverse=True):
            icon = '🟢' if s['type'] == 'buy' else '🔴'
            print(f"     {icon} {s['name']} (强度: {s['strength']}/10)")
    else:
        print(f"\n  ⚪ 当前无明显买卖信号")

def main():
    parser = argparse.ArgumentParser(description="股票技术指标分析")
    parser.add_argument("code", help="股票代码")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    args = parser.parse_args()

    result = analyze(args.code)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_analysis(result)

if __name__ == "__main__":
    main()
