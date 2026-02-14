#!/usr/bin/env python3
"""
检查今天是否为 A 股交易日
返回码: 0=非交易日, 1=是交易日
"""
import sys
from datetime import datetime

try:
    import akshare as ak
except ImportError:
    print("ERROR: akshare not installed. Run: pip3 install akshare", file=sys.stderr)
    sys.exit(2)

def is_trading_day(date_str=None):
    """
    检查指定日期（默认今天）是否为交易日
    date_str: YYYY-MM-DD 格式，默认今天
    """
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
    
    try:
        # 获取交易日历（当年）
        year = date_str[:4]
        calendar = ak.tool_trade_date_hist_sina()
        
        # 检查日期是否在交易日列表中
        trading_dates = calendar['trade_date'].astype(str).tolist()
        return date_str in trading_dates
    except Exception as e:
        print(f"ERROR: Failed to fetch trading calendar: {e}", file=sys.stderr)
        sys.exit(2)

if __name__ == "__main__":
    date = sys.argv[1] if len(sys.argv) > 1 else None
    
    if is_trading_day(date):
        print("是交易日")
        sys.exit(1)
    else:
        print("非交易日")
        sys.exit(0)
