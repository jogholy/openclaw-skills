#!/usr/bin/env python3
"""
价格提醒管理
设置目标价位，到价推送 Telegram
"""
import argparse
import json
import os
import sys

from config import DATA_DIR

ALERTS_FILE = os.path.join(DATA_DIR, "price_alerts.json")

def _read_alerts():
    if not os.path.exists(ALERTS_FILE):
        return []
    with open(ALERTS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def _save_alerts(alerts):
    with open(ALERTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(alerts, f, ensure_ascii=False, indent=2)

def cmd_add(args):
    """添加价格提醒"""
    alerts = _read_alerts()
    alert = {
        "code": args.code,
        "name": args.name or args.code,
        "condition": args.condition,  # "above" or "below"
        "price": args.price,
        "note": args.note or "",
        "triggered": False,
        "one_shot": not args.repeat,
    }
    alerts.append(alert)
    _save_alerts(alerts)
    cond_text = "涨到" if args.condition == "above" else "跌到"
    print(f"✅ 已设置: {alert['name']}({alert['code']}) {cond_text} ¥{args.price:.2f} 时提醒")

def cmd_list(args):
    """列出所有提醒"""
    alerts = _read_alerts()
    if not alerts:
        print("暂无价格提醒")
        return
    
    for i, a in enumerate(alerts):
        status = "✅" if not a["triggered"] else "🔕"
        cond = "≥" if a["condition"] == "above" else "≤"
        repeat = "🔁" if not a.get("one_shot", True) else ""
        print(f"  {status} [{i}] {a['name']}({a['code']}) {cond} ¥{a['price']:.2f} {repeat} {a.get('note','')}")

def cmd_remove(args):
    """删除提醒"""
    alerts = _read_alerts()
    idx = args.index
    if idx < 0 or idx >= len(alerts):
        print(f"❌ 索引 {idx} 无效", file=sys.stderr)
        sys.exit(1)
    removed = alerts.pop(idx)
    _save_alerts(alerts)
    print(f"✅ 已删除: {removed['name']} 的提醒")

def cmd_clear(args):
    """清空所有提醒"""
    _save_alerts([])
    print("✅ 已清空所有价格提醒")

def main():
    parser = argparse.ArgumentParser(description="价格提醒管理")
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("add")
    p.add_argument("--code", required=True)
    p.add_argument("--name", default="")
    p.add_argument("--condition", choices=["above", "below"], required=True)
    p.add_argument("--price", type=float, required=True)
    p.add_argument("--note", default="")
    p.add_argument("--repeat", action="store_true", help="重复提醒（不触发后删除）")

    sub.add_parser("list")

    p = sub.add_parser("remove")
    p.add_argument("--index", type=int, required=True)

    sub.add_parser("clear")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    {"add": cmd_add, "list": cmd_list, "remove": cmd_remove, "clear": cmd_clear}[args.command](args)

if __name__ == "__main__":
    main()
