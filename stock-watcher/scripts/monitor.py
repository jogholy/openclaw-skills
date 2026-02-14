#!/usr/bin/env python3
"""
信号监控 - 定时扫描自选股，检测买卖信号 + 价格提醒
输出格式化的提醒文本，供 cron 任务推送到 Telegram

用法:
  python3 monitor.py                # 扫描所有自选股
  python3 monitor.py --json         # JSON 输出
  python3 monitor.py --check-alerts # 同时检查价格提醒
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
ALERTS_FILE = os.path.join(DATA_DIR, "price_alerts.json")
SIGNAL_HISTORY_FILE = os.path.join(DATA_DIR, "signal_history.json")


def _read_json(path, default=None):
    if not os.path.exists(path):
        return default if default is not None else {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return default if default is not None else {}


def _write_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _load_watchlist():
    if not os.path.exists(WATCHLIST_FILE):
        return []
    with open(WATCHLIST_FILE, 'r', encoding='utf-8') as f:
        lines = [l.strip() for l in f if l.strip()]
    stocks = []
    for line in lines:
        parts = line.split('|')
        if len(parts) == 2:
            stocks.append((parts[0], parts[1]))
    return stocks


def _load_portfolio_positions():
    p = _read_json(PORTFOLIO_FILE, {})
    return p.get("positions", {})


def _load_signal_history():
    return _read_json(SIGNAL_HISTORY_FILE, {})


def _save_signal_history(history):
    _write_json(SIGNAL_HISTORY_FILE, history)


def _is_new_signal(history, code, signal_name):
    """检查信号是否是新的（24小时内未触发过）"""
    key = f"{code}:{signal_name}"
    last = history.get(key)
    if not last:
        return True
    try:
        last_time = datetime.fromisoformat(last)
        return (datetime.now(CST) - last_time).total_seconds() > 86400
    except (ValueError, TypeError):
        return True


def _record_signal(history, code, signal_name):
    key = f"{code}:{signal_name}"
    history[key] = datetime.now(CST).isoformat()


def check_price_alerts(quotes):
    """检查价格提醒"""
    if not os.path.exists(ALERTS_FILE):
        return []

    alerts = _read_json(ALERTS_FILE, [])
    triggered = []
    remaining = []

    for a in alerts:
        if a.get("triggered") and a.get("one_shot", True):
            continue

        code = a["code"]
        q = quotes.get(code)
        if not q:
            remaining.append(a)
            continue

        price = q["price"]
        hit = False
        if a["condition"] == "above" and price >= a["price"]:
            hit = True
        elif a["condition"] == "below" and price <= a["price"]:
            hit = True

        if hit:
            cond_text = "突破" if a["condition"] == "above" else "跌破"
            triggered.append({
                "code": code,
                "name": a["name"],
                "message": f"💰 {a['name']}({code}) 已{cond_text} ¥{a['price']:.2f}，现价 ¥{price:.2f}",
                "note": a.get("note", ""),
            })
            if a.get("one_shot", True):
                a["triggered"] = True
                remaining.append(a)
            else:
                remaining.append(a)
        else:
            remaining.append(a)

    _write_json(ALERTS_FILE, remaining)
    return triggered


def scan_signals():
    """扫描所有自选股的技术信号"""
    stocks = _load_watchlist()
    positions = _load_portfolio_positions()

    if not stocks:
        return {"signals": [], "alerts": [], "error": "自选股列表为空"}

    # 获取实时行情
    quotes = fetch_realtime_quotes(stocks)

    # 加载信号历史（去重用）
    history = _load_signal_history()

    all_signals = []
    for code, name in stocks:
        try:
            result = analyze(code)
            if "error" in result:
                continue

            signals = result.get("signals", [])
            if not signals:
                continue

            q = quotes.get(code, {})
            current_price = q.get("price", result.get("close", 0))
            change_pct = q.get("change_pct", 0)

            # 持仓信息
            pos = positions.get(code)
            pos_info = ""
            if pos:
                pnl_pct = ((current_price - pos["avg_cost"]) / pos["avg_cost"] * 100) if pos["avg_cost"] else 0
                pos_info = f"  持仓 {pos['shares']}股 | 成本 {pos['avg_cost']:.3f} | 浮盈 {'+' if pnl_pct >= 0 else ''}{pnl_pct:.2f}%"

            for sig in signals:
                if not _is_new_signal(history, code, sig["name"]):
                    continue

                _record_signal(history, code, sig["name"])
                icon = "🟢" if sig["type"] == "buy" else "🔴"
                all_signals.append({
                    "code": code,
                    "name": name,
                    "signal": sig["name"],
                    "type": sig["type"],
                    "strength": sig["strength"],
                    "price": current_price,
                    "change_pct": change_pct,
                    "pos_info": pos_info,
                    "message": f"{icon} {name}({code}) — {sig['name']}（强度 {sig['strength']}/10）\n  现价 ¥{current_price:.2f} ({'+' if change_pct >= 0 else ''}{change_pct:.2f}%){pos_info}",
                })

        except Exception as e:
            sys.stderr.write(f"分析 {code} 失败: {e}\n")
            continue

    _save_signal_history(history)

    # 价格提醒
    alerts = check_price_alerts(quotes)

    return {"signals": all_signals, "alerts": alerts}


def format_report(result):
    """格式化为 Telegram 消息"""
    lines = []

    signals = result.get("signals", [])
    alerts = result.get("alerts", [])

    if not signals and not alerts:
        return ""  # 无事发生，不推送

    now = datetime.now(CST).strftime("%H:%M")

    if signals:
        lines.append(f"⚡ 信号提醒 ({now})\n")
        # 按强度排序
        for s in sorted(signals, key=lambda x: x["strength"], reverse=True):
            lines.append(s["message"])
        lines.append("")

    if alerts:
        lines.append(f"💰 价格提醒\n")
        for a in alerts:
            lines.append(a["message"])
            if a.get("note"):
                lines.append(f"  备注: {a['note']}")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="信号监控")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--check-alerts", action="store_true", default=True)
    args = parser.parse_args()

    result = scan_signals()

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        report = format_report(result)
        if report:
            print(report)
        else:
            print("✅ 当前无新信号")


if __name__ == "__main__":
    main()
