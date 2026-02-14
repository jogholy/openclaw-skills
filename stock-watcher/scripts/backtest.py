#!/usr/bin/env python3
"""
股票信号回测脚本
对 technical.py 中的买卖信号做历史回测验证，统计准确率和收益表现
"""
import argparse
import json
import os
import sys
from datetime import datetime

# 添加当前目录到 Python 路径
sys.path.insert(0, os.path.dirname(__file__))

import technical
import config

def detect_signals_for_day(klines, day_idx):
    """
    检测指定日期的信号（复用 technical.py 的逻辑）
    返回: [(signal_name, signal_type, strength), ...]
    """
    if day_idx < 30:  # 需要足够的历史数据计算指标
        return []
    
    # 截取到当前日期的数据
    current_klines = klines[:day_idx + 1]
    closes = [k['close'] for k in current_klines]
    
    # 计算指标（复用 technical.py 的函数）
    ma5 = technical.calc_ma(closes, 5)
    ma10 = technical.calc_ma(closes, 10)
    ma20 = technical.calc_ma(closes, 20)
    ma60 = technical.calc_ma(closes, 60)
    
    dif, dea, macd_hist = technical.calc_macd(closes)
    k_vals, d_vals, j_vals = technical.calc_kdj(current_klines)
    rsi6 = technical.calc_rsi(closes, 6)
    rsi14 = technical.calc_rsi(closes, 14)
    boll_mid, boll_upper, boll_lower = technical.calc_boll(closes)
    
    # 信号检测（与 technical.py 的 analyze() 函数完全一致）
    signals = []
    latest = current_klines[-1]
    
    # MA 金叉/死叉
    if len(ma5) >= 2 and len(ma10) >= 2 and ma5[-1] and ma10[-1] and ma5[-2] and ma10[-2]:
        if ma5[-2] <= ma10[-2] and ma5[-1] > ma10[-1]:
            signals.append(("MA5/10金叉", "buy", 6))
        elif ma5[-2] >= ma10[-2] and ma5[-1] < ma10[-1]:
            signals.append(("MA5/10死叉", "sell", 6))

    if len(ma5) >= 2 and len(ma20) >= 2 and ma5[-1] and ma20[-1] and ma5[-2] and ma20[-2]:
        if ma5[-2] <= ma20[-2] and ma5[-1] > ma20[-1]:
            signals.append(("MA5/20金叉", "buy", 7))
        elif ma5[-2] >= ma20[-2] and ma5[-1] < ma20[-1]:
            signals.append(("MA5/20死叉", "sell", 7))

    # MACD 金叉/死叉
    if len(dif) >= 2 and len(dea) >= 2:
        if dif[-2] <= dea[-2] and dif[-1] > dea[-1]:
            signals.append(("MACD金叉", "buy", 7))
        elif dif[-2] >= dea[-2] and dif[-1] < dea[-1]:
            signals.append(("MACD死叉", "sell", 7))

    # KDJ 超买超卖
    if k_vals[-1] < 20 and d_vals[-1] < 20:
        signals.append(("KDJ超卖区", "buy", 5))
    elif k_vals[-1] > 80 and d_vals[-1] > 80:
        signals.append(("KDJ超买区", "sell", 5))

    # KDJ 金叉/死叉
    if len(k_vals) >= 2 and len(d_vals) >= 2:
        if k_vals[-2] <= d_vals[-2] and k_vals[-1] > d_vals[-1] and k_vals[-1] < 50:
            signals.append(("KDJ低位金叉", "buy", 7))
        elif k_vals[-2] >= d_vals[-2] and k_vals[-1] < d_vals[-1] and k_vals[-1] > 50:
            signals.append(("KDJ高位死叉", "sell", 7))

    # RSI 超买超卖
    if rsi6[-1] and rsi6[-1] < 20:
        signals.append(("RSI6超卖(<20)", "buy", 6))
    elif rsi6[-1] and rsi6[-1] > 80:
        signals.append(("RSI6超买(>80)", "sell", 6))

    # 布林带
    if boll_lower[-1] and latest['close'] <= boll_lower[-1]:
        signals.append(("触及布林下轨", "buy", 5))
    elif boll_upper[-1] and latest['close'] >= boll_upper[-1]:
        signals.append(("触及布林上轨", "sell", 5))

    # 均线多头/空头排列
    if ma5[-1] and ma10[-1] and ma20[-1]:
        if ma5[-1] > ma10[-1] > ma20[-1]:
            signals.append(("均线多头排列", "buy", 8))
        elif ma5[-1] < ma10[-1] < ma20[-1]:
            signals.append(("均线空头排列", "sell", 8))
    
    return signals

def calculate_returns(klines, trigger_idx, periods=[1, 3, 5, 10, 20]):
    """计算触发信号后各持有期的收益率"""
    trigger_price = klines[trigger_idx]['close']
    returns = {}
    
    for period in periods:
        future_idx = trigger_idx + period
        if future_idx < len(klines):
            future_price = klines[future_idx]['close']
            return_rate = (future_price - trigger_price) / trigger_price
            returns[f"{period}d"] = return_rate
        else:
            returns[f"{period}d"] = None
    
    return returns

def backtest_stock(code, signal_filter=None):
    """回测单只股票"""
    try:
        name, klines = technical.fetch_daily_klines(code, 250)
    except Exception as e:
        return {"error": f"获取数据失败: {e}"}
    
    if len(klines) < 50:
        return {"error": f"数据不足（仅 {len(klines)} 天）"}
    
    # 信号统计
    signal_stats = {}
    
    # 从第30天开始逐日扫描
    for day_idx in range(30, len(klines)):
        signals = detect_signals_for_day(klines, day_idx)
        
        for signal_name, signal_type, strength in signals:
            # 过滤特定信号
            if signal_filter and signal_filter not in signal_name:
                continue
                
            if signal_name not in signal_stats:
                signal_stats[signal_name] = {
                    "type": signal_type,
                    "count": 0,
                    "periods": {
                        "1d": {"wins": 0, "total": 0, "returns": []},
                        "3d": {"wins": 0, "total": 0, "returns": []},
                        "5d": {"wins": 0, "total": 0, "returns": []},
                        "10d": {"wins": 0, "total": 0, "returns": []},
                        "20d": {"wins": 0, "total": 0, "returns": []},
                    }
                }
            
            signal_stats[signal_name]["count"] += 1
            returns = calculate_returns(klines, day_idx)
            
            # 统计各持有期表现
            for period, return_rate in returns.items():
                if return_rate is not None:
                    stats = signal_stats[signal_name]["periods"][period]
                    stats["total"] += 1
                    stats["returns"].append(return_rate)
                    
                    # 判断胜负
                    if signal_type == "buy":
                        # 买入信号：正收益算胜
                        if return_rate > 0:
                            stats["wins"] += 1
                    else:
                        # 卖出信号：负收益算胜（做对了）
                        if return_rate < 0:
                            stats["wins"] += 1
    
    # 计算胜率和平均收益
    for signal_name, stats in signal_stats.items():
        for period, period_stats in stats["periods"].items():
            if period_stats["total"] > 0:
                period_stats["win_rate"] = period_stats["wins"] / period_stats["total"]
                period_stats["avg_return"] = sum(period_stats["returns"]) / len(period_stats["returns"])
                period_stats["max_profit"] = max(period_stats["returns"]) if period_stats["returns"] else 0
                period_stats["max_loss"] = min(period_stats["returns"]) if period_stats["returns"] else 0
            else:
                period_stats["win_rate"] = 0
                period_stats["avg_return"] = 0
                period_stats["max_profit"] = 0
                period_stats["max_loss"] = 0
    
    # 找出最可靠的信号
    best_buy_signal = None
    best_sell_signal = None
    best_buy_score = 0
    best_sell_score = 0
    
    for signal_name, stats in signal_stats.items():
        if stats["count"] >= 3:  # 至少触发3次才考虑
            # 以5日胜率为主要评判标准
            score = stats["periods"]["5d"]["win_rate"] * 100
            if stats["type"] == "buy" and score > best_buy_score:
                best_buy_score = score
                best_buy_signal = signal_name
            elif stats["type"] == "sell" and score > best_sell_score:
                best_sell_score = score
                best_sell_signal = signal_name
    
    # 计算综合得分
    total_signals = sum(stats["count"] for stats in signal_stats.values())
    avg_win_rate = 0
    if signal_stats:
        win_rates = []
        for stats in signal_stats.values():
            if stats["periods"]["5d"]["total"] > 0:
                win_rates.append(stats["periods"]["5d"]["win_rate"])
        avg_win_rate = sum(win_rates) / len(win_rates) if win_rates else 0
    
    overall_score = min(10, avg_win_rate * 10 + (total_signals / len(klines)) * 50)
    
    return {
        "code": code,
        "name": name,
        "data_range": {
            "start": klines[0]["date"],
            "end": klines[-1]["date"],
            "days": len(klines)
        },
        "signals": signal_stats,
        "best_buy_signal": best_buy_signal,
        "best_sell_signal": best_sell_signal,
        "overall_score": round(overall_score, 1)
    }

def print_backtest_result(result):
    """打印回测结果（文本格式）"""
    if "error" in result:
        print(f"❌ {result['error']}")
        return
    
    print(f"═══ {result['name']}({result['code']}) 信号回测 ═══")
    data_range = result["data_range"]
    print(f"数据范围: {data_range['start']} ~ {data_range['end']} (共 {data_range['days']} 个交易日)")
    print()
    
    # 分类显示买入和卖出信号
    buy_signals = {k: v for k, v in result["signals"].items() if v["type"] == "buy"}
    sell_signals = {k: v for k, v in result["signals"].items() if v["type"] == "sell"}
    
    if buy_signals:
        print("📊 买入信号统计:")
        for signal_name, stats in sorted(buy_signals.items(), key=lambda x: x[1]["count"], reverse=True):
            print(f"  {signal_name} (触发 {stats['count']} 次)")
            for period in ["1d", "3d", "5d", "10d", "20d"]:
                period_stats = stats["periods"][period]
                if period_stats["total"] > 0:
                    win_rate = period_stats["win_rate"] * 100
                    avg_return = period_stats["avg_return"] * 100
                    print(f"    {period.replace('d', '日')}胜率: {win_rate:.1f}% | 平均收益: {avg_return:+.1f}%")
            print()
    
    if sell_signals:
        print("📊 卖出信号统计:")
        for signal_name, stats in sorted(sell_signals.items(), key=lambda x: x[1]["count"], reverse=True):
            print(f"  {signal_name} (触发 {stats['count']} 次)")
            for period in ["1d", "3d", "5d", "10d", "20d"]:
                period_stats = stats["periods"][period]
                if period_stats["total"] > 0:
                    win_rate = period_stats["win_rate"] * 100
                    avg_return = period_stats["avg_return"] * 100
                    print(f"    {period.replace('d', '日')}胜率: {win_rate:.1f}% | 平均收益: {avg_return:+.1f}%")
            print()
    
    print("📊 综合评估:")
    if result["best_buy_signal"]:
        buy_win_rate = result["signals"][result["best_buy_signal"]]["periods"]["5d"]["win_rate"] * 100
        print(f"  最可靠买入信号: {result['best_buy_signal']} (5日胜率 {buy_win_rate:.0f}%)")
    else:
        print("  最可靠买入信号: 无")
    
    if result["best_sell_signal"]:
        sell_win_rate = result["signals"][result["best_sell_signal"]]["periods"]["5d"]["win_rate"] * 100
        print(f"  最可靠卖出信号: {result['best_sell_signal']} (5日胜率 {sell_win_rate:.0f}%)")
    else:
        print("  最可靠卖出信号: 无")
    
    print(f"  信号综合得分: {result['overall_score']}/10")

def load_watchlist():
    """加载自选股列表"""
    try:
        with open(config.WATCHLIST_FILE, 'r', encoding='utf-8') as f:
            codes = []
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # 提取股票代码（格式可能是 "300098 高新兴" 或 "300098"）
                    code = line.split()[0]
                    codes.append(code)
            return codes
    except FileNotFoundError:
        return []

def main():
    parser = argparse.ArgumentParser(description="股票信号回测")
    parser.add_argument("code", nargs="?", help="股票代码")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    parser.add_argument("--all", action="store_true", help="回测所有自选股")
    parser.add_argument("--signal", help="只看特定信号")
    args = parser.parse_args()
    
    if args.all:
        # 回测所有自选股
        codes = load_watchlist()
        if not codes:
            print("❌ 自选股列表为空，请先添加股票到 watchlist")
            return
        
        results = []
        for code in codes:
            print(f"正在回测 {code}...")
            result = backtest_stock(code, args.signal)
            if args.json:
                results.append(result)
            else:
                print_backtest_result(result)
                print("-" * 50)
        
        if args.json:
            print(json.dumps(results, ensure_ascii=False, indent=2))
    
    elif args.code:
        # 回测单只股票
        result = backtest_stock(args.code, args.signal)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print_backtest_result(result)
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()