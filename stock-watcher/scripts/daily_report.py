#!/usr/bin/env python3
"""
盘前提要 + 盘后总结
盘前(9:15)：持仓股关键信息 + 技术面概览
盘后(15:15)：当日表现 + 信号汇总

用法:
  python3 daily_report.py morning    # 盘前提要
  python3 daily_report.py evening    # 盘后总结
  python3 daily_report.py --json     # JSON 输出
"""
import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(__file__))
from config import DATA_DIR, WATCHLIST_FILE, PORTFOLIO_FILE
from summarize_performance import fetch_realtime_quotes
from technical import analyze

CST = timezone(timedelta(hours=8))


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


def morning_report():
    """盘前提要"""
    stocks = _load_watchlist()
    portfolio = _load_portfolio()
    positions = portfolio.get("positions", {})

    if not stocks:
        return "自选股列表为空"

    today = datetime.now(CST).strftime("%m/%d")
    weekday = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][datetime.now(CST).weekday()]
    lines = [f"☀️ 盘前提要 {today} {weekday}\n"]

    # 账户概览
    cash = portfolio.get("total_cash", 0)
    initial = portfolio.get("initial_capital", 0)
    if initial > 0:
        lines.append(f"💰 可用资金: ¥{cash:,.2f}")

    # 持仓股技术面
    if positions:
        lines.append(f"\n📊 持仓股分析:")
        for code, pos in positions.items():
            try:
                result = analyze(code)
                if "error" in result:
                    lines.append(f"  {pos['name']}({code}) — 数据获取失败")
                    continue

                ind = result["indicators"]
                signals = result.get("signals", [])
                close = result["close"]
                pnl_pct = ((close - pos["avg_cost"]) / pos["avg_cost"] * 100) if pos["avg_cost"] else 0
                sign = "+" if pnl_pct >= 0 else ""

                lines.append(f"\n  {'🟢' if pnl_pct >= 0 else '🔴'} {pos['name']}({code})")
                lines.append(f"  昨收 {close} | 成本 {pos['avg_cost']:.3f} | 浮盈 {sign}{pnl_pct:.2f}%")

                # 关键指标一行
                kdj = ind["kdj"]
                macd = ind["macd"]
                lines.append(f"  MA5:{ind['ma5']} MA20:{ind['ma20']} RSI:{ind['rsi6']}")
                lines.append(f"  MACD柱:{macd['hist']} KDJ:{kdj['k']:.0f}/{kdj['d']:.0f}/{kdj['j']:.0f}")

                # 信号
                if signals:
                    for s in sorted(signals, key=lambda x: x["strength"], reverse=True)[:3]:
                        icon = "🟢" if s["type"] == "buy" else "🔴"
                        lines.append(f"  {icon} {s['name']}（{s['strength']}/10）")

            except Exception as e:
                lines.append(f"  {pos['name']}({code}) — 分析失败: {e}")

    # 关注股（非持仓）
    watch_only = [(c, n) for c, n in stocks if c not in positions]
    if watch_only:
        lines.append(f"\n👀 关注股:")
        for code, name in watch_only:
            try:
                result = analyze(code)
                if "error" in result:
                    continue
                signals = result.get("signals", [])
                buy_signals = [s for s in signals if s["type"] == "buy" and s["strength"] >= 6]
                if buy_signals:
                    sig_text = ", ".join(s["name"] for s in buy_signals)
                    lines.append(f"  🟢 {name}({code}) 昨收{result['close']} — {sig_text}")
                else:
                    lines.append(f"  ⚪ {name}({code}) 昨收{result['close']} — 无明显信号")
            except Exception:
                continue

    lines.append(f"\n祝今天交易顺利 🍀")
    return "\n".join(lines)


def evening_report():
    """盘后总结"""
    stocks = _load_watchlist()
    portfolio = _load_portfolio()
    positions = portfolio.get("positions", {})

    if not stocks:
        return "自选股列表为空"

    # 获取实时行情
    quotes = fetch_realtime_quotes(stocks)

    today = datetime.now(CST).strftime("%m/%d")
    lines = [f"🌙 盘后总结 {today}\n"]

    # 账户概览
    cash = portfolio.get("total_cash", 0)
    initial = portfolio.get("initial_capital", 0)
    market_value = 0
    daily_pnl = 0

    if positions:
        lines.append("📊 持仓表现:")
        for code, pos in positions.items():
            q = quotes.get(code)
            if not q:
                lines.append(f"  {pos['name']}({code}) — 行情获取失败")
                continue

            mv = q["price"] * pos["shares"]
            market_value += mv
            day_change = q["change"] * pos["shares"]
            daily_pnl += day_change
            total_pnl = mv - pos["total_cost"]
            total_pnl_pct = (total_pnl / pos["total_cost"] * 100) if pos["total_cost"] else 0

            arrow = "🟢" if q["change_pct"] >= 0 else "🔴"
            sign_d = "+" if q["change_pct"] >= 0 else ""
            sign_t = "+" if total_pnl >= 0 else ""

            lines.append(f"\n  {arrow} {pos['name']}({code})")
            lines.append(f"  收盘 {q['price']:.2f} ({sign_d}{q['change_pct']:.2f}%)")
            lines.append(f"  今日盈亏: {'+' if day_change >= 0 else ''}¥{day_change:,.2f}")
            lines.append(f"  总盈亏: {sign_t}¥{total_pnl:,.2f} ({sign_t}{total_pnl_pct:.2f}%)")

        total_assets = cash + market_value
        total_pnl_all = total_assets - initial
        total_pnl_pct = (total_pnl_all / initial * 100) if initial else 0

        lines.append(f"\n💰 账户汇总:")
        lines.append(f"  总资产: ¥{total_assets:,.2f}")
        lines.append(f"  今日盈亏: {'+' if daily_pnl >= 0 else ''}¥{daily_pnl:,.2f}")
        lines.append(f"  总盈亏: {'+' if total_pnl_all >= 0 else ''}¥{total_pnl_all:,.2f} ({'+' if total_pnl_pct >= 0 else ''}{total_pnl_pct:.2f}%)")
        lines.append(f"  仓位: {market_value / total_assets * 100:.1f}%" if total_assets else "")

    # 关注股涨跌
    watch_only = [(c, n) for c, n in stocks if c not in positions]
    if watch_only:
        lines.append(f"\n👀 关注股:")
        for code, name in watch_only:
            q = quotes.get(code)
            if q:
                arrow = "🟢" if q["change_pct"] >= 0 else "🔴"
                sign = "+" if q["change_pct"] >= 0 else ""
                lines.append(f"  {arrow} {name} {q['price']:.2f} ({sign}{q['change_pct']:.2f}%)")

    # 技术信号汇总
    lines.append(f"\n⚡ 信号汇总:")
    for code, name in stocks:
        try:
            result = analyze(code)
            signals = result.get("signals", [])
            if signals:
                strong = [s for s in signals if s["strength"] >= 6]
                if strong:
                    sig_text = ", ".join(f"{'🟢' if s['type'] == 'buy' else '🔴'}{s['name']}" for s in strong)
                    lines.append(f"  {name}: {sig_text}")
        except Exception:
            continue

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="盘前提要 / 盘后总结")
    parser.add_argument("mode", choices=["morning", "evening"], help="morning=盘前, evening=盘后")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.mode == "morning":
        report = morning_report()
    else:
        report = evening_report()

    print(report)


if __name__ == "__main__":
    main()
