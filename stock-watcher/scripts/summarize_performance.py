#!/usr/bin/env python3
"""
股票行情摘要 - 使用腾讯行情 API 获取实时数据
数据源: qt.gtimg.cn (免费、无需 API key、延迟约1-3分钟)
"""
import os
import sys
import json
import urllib.request

WATCHLIST_FILE = os.path.expanduser("~/.clawdbot/stock_watcher/watchlist.txt")

def get_market_prefix(code):
    """根据股票代码判断市场前缀"""
    if code.startswith(('6', '5')):
        return 'sh'
    else:
        return 'sz'

def fetch_realtime_quotes(stocks):
    """批量获取实时行情"""
    if not stocks:
        return {}
    
    symbols = ','.join(f"{get_market_prefix(code)}{code}" for code, _ in stocks)
    url = f"https://qt.gtimg.cn/q={symbols}"
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    req = urllib.request.Request(url, headers=headers)
    
    with urllib.request.urlopen(req, timeout=10) as resp:
        raw = resp.read().decode('gbk', errors='replace')
    
    results = {}
    for line in raw.strip().split(';'):
        line = line.strip()
        if not line or '=' not in line:
            continue
        
        # v_sh600053="1~九鼎投资~600053~18.69~..."
        key, _, val = line.partition('=')
        val = val.strip('"')
        fields = val.split('~')
        
        if len(fields) < 50:
            continue
        
        code = fields[2]
        try:
            results[code] = {
                'name': fields[1],
                'code': code,
                'price': float(fields[3]) if fields[3] else 0,
                'prev_close': float(fields[4]) if fields[4] else 0,
                'open': float(fields[5]) if fields[5] else 0,
                'volume': int(fields[6]) if fields[6] else 0,
                'high': float(fields[33]) if fields[33] else 0,
                'low': float(fields[34]) if fields[34] else 0,
                'change': float(fields[31]) if fields[31] else 0,
                'change_pct': float(fields[32]) if fields[32] else 0,
                'turnover': float(fields[38]) if fields[38] else 0,  # 换手率
                'amount': float(fields[37]) if fields[37] else 0,    # 成交额(万)
                'pe': float(fields[39]) if fields[39] else 0,        # 市盈率
                'market_cap': float(fields[45]) if fields[45] else 0, # 总市值(亿)
                'time': fields[30] if len(fields) > 30 else '',
            }
        except (ValueError, IndexError):
            continue
    
    return results

def format_amount(amount_wan):
    """格式化成交额(万元)"""
    if amount_wan >= 10000:
        return f"{amount_wan/10000:.2f}亿"
    return f"{amount_wan:.0f}万"

def summarize():
    """输出行情摘要"""
    if not os.path.exists(WATCHLIST_FILE):
        print("自选股列表为空")
        return
    
    with open(WATCHLIST_FILE, 'r', encoding='utf-8') as f:
        lines = [l.strip() for l in f if l.strip()]
    
    if not lines:
        print("自选股列表为空")
        return
    
    stocks = []
    for line in lines:
        parts = line.split('|')
        if len(parts) == 2:
            stocks.append((parts[0], parts[1]))
    
    if not stocks:
        print("自选股列表格式错误")
        return
    
    quotes = fetch_realtime_quotes(stocks)
    
    # JSON 输出模式
    if '--json' in sys.argv:
        print(json.dumps(quotes, ensure_ascii=False, indent=2))
        return
    
    # 人类可读输出
    for code, name in stocks:
        q = quotes.get(code)
        if not q:
            print(f"{code} {name} — 数据获取失败")
            continue
        
        arrow = '🔴' if q['change_pct'] < 0 else ('🟢' if q['change_pct'] > 0 else '⚪')
        sign = '+' if q['change_pct'] > 0 else ''
        
        print(f"{arrow} {q['name']} ({code})")
        print(f"   现价: {q['price']:.2f}  {sign}{q['change']:.2f} ({sign}{q['change_pct']:.2f}%)")
        print(f"   今开: {q['open']:.2f}  最高: {q['high']:.2f}  最低: {q['low']:.2f}")
        print(f"   成交额: {format_amount(q['amount'])}  换手: {q['turnover']:.2f}%")
        if q['pe'] > 0:
            print(f"   市盈率: {q['pe']:.2f}  市值: {q['market_cap']:.2f}亿")
        print()

if __name__ == "__main__":
    summarize()
