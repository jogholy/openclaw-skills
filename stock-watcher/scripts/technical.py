#!/usr/bin/env python3
"""
技术指标分析模块 v2
使用 stock_analysis 库进行指标计算
数据源：同花顺日线 API
"""
import argparse
import json
import sys
import urllib.request
import re
from datetime import datetime, timedelta, timezone
import pandas as pd

# 导入新的指标库
from stock_analysis import indicators

CST = timezone(timedelta(hours=8))

# ── 数据获取 ──────────────────────────────────────────

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
            'date': parts[0],
            'open': float(parts[1]),
            'high': float(parts[2]),
            'low': float(parts[3]),
            'close': float(parts[4]),
            'volume': int(parts[5]),
        })

    return name, klines

def klines_to_dataframe(klines):
    """转换K线数据为 DataFrame"""
    df = pd.DataFrame(klines)
    df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
    df.set_index('date', inplace=True)
    return df

# ── 指标分析 ──────────────────────────────────────────

def analyze_stock(code, days=250):
    """分析股票技术指标"""
    name, klines = fetch_daily_klines(code, days)
    
    if len(klines) < 60:
        return {
            'error': f'数据不足（需要至少60天，当前{len(klines)}天）',
            'code': code,
            'name': name
        }
    
    df = klines_to_dataframe(klines)
    latest = klines[-1]
    
    # 使用新库计算指标
    try:
        # MA 系统
        ma_dict = indicators.ma_system(df['close'])
        
        # MACD
        macd_line, signal_line, histogram = indicators.macd(df['close'])
        
        # RSI
        rsi = indicators.rsi(df['close'])
        
        # KDJ
        k, d, j = indicators.kdj(df['high'], df['low'], df['close'])
        
        # 布林带
        upper, middle, lower = indicators.bollinger_bands(df['close'])
        
        # OBV
        obv = indicators.obv(df['close'], df['volume'])
        
    except Exception as e:
        return {
            'error': f'指标计算失败: {str(e)}',
            'code': code,
            'name': name
        }
    
    # 构建结果
    result = {
        'code': code,
        'name': name,
        'date': latest['date'],
        'price': latest['close'],
        'volume': latest['volume'],
        'ma': {
            'ma5': round(ma_dict['MA5'].iloc[-1], 2) if not pd.isna(ma_dict['MA5'].iloc[-1]) else None,
            'ma10': round(ma_dict['MA10'].iloc[-1], 2) if not pd.isna(ma_dict['MA10'].iloc[-1]) else None,
            'ma20': round(ma_dict['MA20'].iloc[-1], 2) if not pd.isna(ma_dict['MA20'].iloc[-1]) else None,
            'ma60': round(ma_dict['MA60'].iloc[-1], 2) if not pd.isna(ma_dict['MA60'].iloc[-1]) else None,
        },
        'macd': {
            'dif': round(macd_line.iloc[-1], 4) if not pd.isna(macd_line.iloc[-1]) else None,
            'dea': round(signal_line.iloc[-1], 4) if not pd.isna(signal_line.iloc[-1]) else None,
            'macd': round(histogram.iloc[-1], 4) if not pd.isna(histogram.iloc[-1]) else None,
        },
        'kdj': {
            'k': round(k.iloc[-1], 2) if not pd.isna(k.iloc[-1]) else None,
            'd': round(d.iloc[-1], 2) if not pd.isna(d.iloc[-1]) else None,
            'j': round(j.iloc[-1], 2) if not pd.isna(j.iloc[-1]) else None,
        },
        'rsi': {
            'rsi14': round(rsi.iloc[-1], 2) if not pd.isna(rsi.iloc[-1]) else None,
        },
        'boll': {
            'upper': round(upper.iloc[-1], 2) if not pd.isna(upper.iloc[-1]) else None,
            'middle': round(middle.iloc[-1], 2) if not pd.isna(middle.iloc[-1]) else None,
            'lower': round(lower.iloc[-1], 2) if not pd.isna(lower.iloc[-1]) else None,
        },
        'obv': {
            'value': int(obv.iloc[-1]) if not pd.isna(obv.iloc[-1]) else None,
        }
    }
    
    # 生成信号
    signals = []
    
    # MA 信号
    price = latest['close']
    if result['ma']['ma5'] and result['ma']['ma10']:
        if result['ma']['ma5'] > result['ma']['ma10']:
            signals.append('MA5上穿MA10（金叉）')
        elif result['ma']['ma5'] < result['ma']['ma10']:
            signals.append('MA5下穿MA10（死叉）')
    
    # MACD 信号
    if result['macd']['dif'] and result['macd']['dea']:
        if result['macd']['dif'] > result['macd']['dea'] and result['macd']['macd'] > 0:
            signals.append('MACD金叉（多头）')
        elif result['macd']['dif'] < result['macd']['dea'] and result['macd']['macd'] < 0:
            signals.append('MACD死叉（空头）')
    
    # RSI 信号
    if result['rsi']['rsi14']:
        if result['rsi']['rsi14'] > 70:
            signals.append('RSI超买（>70）')
        elif result['rsi']['rsi14'] < 30:
            signals.append('RSI超卖（<30）')
    
    # KDJ 信号
    if result['kdj']['k'] and result['kdj']['d']:
        if result['kdj']['k'] > 80 and result['kdj']['d'] > 80:
            signals.append('KDJ超买区（>80）')
        elif result['kdj']['k'] < 20 and result['kdj']['d'] < 20:
            signals.append('KDJ超卖区（<20）')
    
    result['signals'] = signals
    
    return result

# ── CLI ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='股票技术指标分析（使用 stock_analysis 库）')
    parser.add_argument('code', help='股票代码（如 300098）')
    parser.add_argument('--days', type=int, default=250, help='获取天数（默认250）')
    parser.add_argument('--json', action='store_true', help='输出JSON格式')
    
    args = parser.parse_args()
    
    try:
        result = analyze_stock(args.code, args.days)
        
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            if 'error' in result:
                print(f"❌ {result['error']}")
                sys.exit(1)
            
            print(f"\n📊 {result['name']} ({result['code']}) - {result['date']}")
            print(f"💰 最新价: ¥{result['price']}")
            print(f"\n📈 均线系统:")
            print(f"  MA5:  {result['ma']['ma5']}")
            print(f"  MA10: {result['ma']['ma10']}")
            print(f"  MA20: {result['ma']['ma20']}")
            print(f"  MA60: {result['ma']['ma60']}")
            
            print(f"\n📉 MACD:")
            print(f"  DIF: {result['macd']['dif']}")
            print(f"  DEA: {result['macd']['dea']}")
            print(f"  MACD: {result['macd']['macd']}")
            
            print(f"\n🎯 KDJ:")
            print(f"  K: {result['kdj']['k']}")
            print(f"  D: {result['kdj']['d']}")
            print(f"  J: {result['kdj']['j']}")
            
            print(f"\n💪 RSI(14): {result['rsi']['rsi14']}")
            
            print(f"\n🎈 布林带:")
            print(f"  上轨: {result['boll']['upper']}")
            print(f"  中轨: {result['boll']['middle']}")
            print(f"  下轨: {result['boll']['lower']}")
            
            print(f"\n📊 OBV: {result['obv']['value']:,}")
            
            if result['signals']:
                print(f"\n🚨 交易信号:")
                for sig in result['signals']:
                    print(f"  • {sig}")
            else:
                print(f"\n✅ 无明显信号")
    
    except Exception as e:
        print(f"❌ 错误: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
