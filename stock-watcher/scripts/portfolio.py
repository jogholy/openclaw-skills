#!/usr/bin/env python3
"""
资金仓位管理模块
管理虚拟账户：总资金、可用资金、持仓、交易流水
"""
import argparse
import json
import os
import sys
import fcntl
from datetime import datetime, timedelta, timezone

from config import PORTFOLIO_FILE, TRADES_FILE

CST = timezone(timedelta(hours=8))

# ── 数据读写 ──────────────────────────────────────────

def _read_json(path, default=None):
    if not os.path.exists(path):
        return default if default is not None else {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_SH)
            content = f.read().strip()
            return json.loads(content) if content else (default if default is not None else {})
    except (json.JSONDecodeError, FileNotFoundError):
        return default if default is not None else {}

def _write_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        json.dump(data, f, ensure_ascii=False, indent=2)

# ── Portfolio CRUD ────────────────────────────────────

def _get_portfolio():
    default = {
        "total_cash": 0,        # 可用资金
        "initial_capital": 0,   # 初始资金（用于算总收益率）
        "positions": {},        # {code: {name, shares, avg_cost, total_cost}}
        "created_at": None,
    }
    p = _read_json(PORTFOLIO_FILE, default)
    # 兼容旧数据
    if "positions" not in p:
        p["positions"] = {}
    return p

def _save_portfolio(p):
    _write_json(PORTFOLIO_FILE, p)

def _get_trades():
    return _read_json(TRADES_FILE, [])

def _save_trades(trades):
    _write_json(TRADES_FILE, trades)

def _now_str():
    return datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S")

def _add_trade(action, code, name, shares, price, amount, note=""):
    trades = _get_trades()
    trades.append({
        "time": _now_str(),
        "action": action,
        "code": code,
        "name": name,
        "shares": shares,
        "price": price,
        "amount": amount,
        "note": note,
    })
    _save_trades(trades)

# ── Commands ──────────────────────────────────────────

def cmd_init(args):
    """初始化账户，设置初始资金"""
    p = _get_portfolio()
    capital = args.capital
    if capital <= 0:
        print("初始资金必须大于 0", file=sys.stderr)
        sys.exit(1)
    p["total_cash"] = capital
    p["initial_capital"] = capital
    p["positions"] = {}
    p["created_at"] = _now_str()
    _save_portfolio(p)
    _save_trades([])  # 清空流水
    _add_trade("init", "-", "-", 0, 0, capital, "初始化账户")
    print(f"✅ 账户已初始化，资金: ¥{capital:,.2f}")

def cmd_deposit(args):
    """转入资金"""
    p = _get_portfolio()
    amount = args.amount
    if amount <= 0:
        print("转入金额必须大于 0", file=sys.stderr)
        sys.exit(1)
    p["total_cash"] += amount
    p["initial_capital"] += amount
    _save_portfolio(p)
    _add_trade("deposit", "-", "-", 0, 0, amount, args.note or "转入资金")
    print(f"✅ 转入 ¥{amount:,.2f}，可用资金: ¥{p['total_cash']:,.2f}")

def cmd_withdraw(args):
    """转出资金"""
    p = _get_portfolio()
    amount = args.amount
    if amount <= 0 or amount > p["total_cash"]:
        print(f"转出金额无效（可用: ¥{p['total_cash']:,.2f}）", file=sys.stderr)
        sys.exit(1)
    p["total_cash"] -= amount
    p["initial_capital"] -= amount
    _save_portfolio(p)
    _add_trade("withdraw", "-", "-", 0, 0, -amount, args.note or "转出资金")
    print(f"✅ 转出 ¥{amount:,.2f}，可用资金: ¥{p['total_cash']:,.2f}")

def cmd_buy(args):
    """买入股票"""
    p = _get_portfolio()
    code = args.code
    name = args.name or code
    shares = args.shares
    price = args.price
    cost = round(shares * price, 2)

    if cost > p["total_cash"]:
        print(f"❌ 资金不足！需要 ¥{cost:,.2f}，可用 ¥{p['total_cash']:,.2f}", file=sys.stderr)
        sys.exit(1)

    # 更新持仓
    pos = p["positions"]
    if code in pos:
        old = pos[code]
        new_shares = old["shares"] + shares
        new_total = old["total_cost"] + cost
        pos[code] = {
            "name": name if name != code else old["name"],
            "shares": new_shares,
            "avg_cost": round(new_total / new_shares, 4),
            "total_cost": round(new_total, 2),
        }
    else:
        pos[code] = {
            "name": name,
            "shares": shares,
            "avg_cost": round(price, 4),
            "total_cost": round(cost, 2),
        }

    p["total_cash"] = round(p["total_cash"] - cost, 2)
    _save_portfolio(p)
    _add_trade("buy", code, name, shares, price, -cost)
    print(f"✅ 买入 {name}({code}) {shares}股 × ¥{price:.2f} = ¥{cost:,.2f}")
    print(f"   可用资金: ¥{p['total_cash']:,.2f}")

def cmd_sell(args):
    """卖出股票"""
    p = _get_portfolio()
    code = args.code
    shares = args.shares
    price = args.price

    pos = p["positions"]
    if code not in pos:
        print(f"❌ 未持有 {code}", file=sys.stderr)
        sys.exit(1)

    old = pos[code]
    if shares > old["shares"]:
        print(f"❌ 持仓不足！持有 {old['shares']}股，卖出 {shares}股", file=sys.stderr)
        sys.exit(1)

    income = round(shares * price, 2)
    cost_basis = round(old["avg_cost"] * shares, 2)
    profit = round(income - cost_basis, 2)
    name = old["name"]

    # 更新持仓
    remaining = old["shares"] - shares
    if remaining == 0:
        del pos[code]
    else:
        pos[code] = {
            "name": name,
            "shares": remaining,
            "avg_cost": old["avg_cost"],
            "total_cost": round(old["avg_cost"] * remaining, 2),
        }

    p["total_cash"] = round(p["total_cash"] + income, 2)
    _save_portfolio(p)
    _add_trade("sell", code, name, shares, price, income, f"盈亏: {'+' if profit >= 0 else ''}{profit:.2f}")

    sign = '+' if profit >= 0 else ''
    pct = (profit / cost_basis * 100) if cost_basis else 0
    print(f"✅ 卖出 {name}({code}) {shares}股 × ¥{price:.2f} = ¥{income:,.2f}")
    print(f"   盈亏: {sign}¥{profit:,.2f} ({sign}{pct:.2f}%)")
    print(f"   可用资金: ¥{p['total_cash']:,.2f}")

def cmd_status(args):
    """查看账户状态"""
    p = _get_portfolio()
    if not p.get("created_at"):
        print("账户未初始化，请先运行: portfolio.py init --capital <金额>")
        return

    positions = p.get("positions", {})

    # 获取实时行情计算市值
    market_value = 0
    unrealized_pnl = 0
    pos_details = []

    if positions:
        # 导入行情模块
        sys.path.insert(0, os.path.dirname(__file__))
        from summarize_performance import fetch_realtime_quotes
        stocks = [(code, info["name"]) for code, info in positions.items()]
        quotes = fetch_realtime_quotes(stocks)

        for code, info in positions.items():
            q = quotes.get(code)
            current_price = q["price"] if q else 0
            mv = round(current_price * info["shares"], 2)
            pnl = round(mv - info["total_cost"], 2)
            pnl_pct = (pnl / info["total_cost"] * 100) if info["total_cost"] else 0
            market_value += mv
            unrealized_pnl += pnl
            pos_details.append({
                "code": code,
                "name": info["name"],
                "shares": info["shares"],
                "avg_cost": info["avg_cost"],
                "current_price": current_price,
                "market_value": mv,
                "pnl": pnl,
                "pnl_pct": pnl_pct,
            })

    total_assets = round(p["total_cash"] + market_value, 2)
    total_pnl = round(total_assets - p["initial_capital"], 2)
    total_pnl_pct = (total_pnl / p["initial_capital"] * 100) if p["initial_capital"] else 0

    if args.json:
        print(json.dumps({
            "cash": p["total_cash"],
            "initial_capital": p["initial_capital"],
            "market_value": market_value,
            "total_assets": total_assets,
            "total_pnl": total_pnl,
            "total_pnl_pct": round(total_pnl_pct, 2),
            "unrealized_pnl": unrealized_pnl,
            "positions": pos_details,
        }, ensure_ascii=False, indent=2))
        return

    sign = '+' if total_pnl >= 0 else ''
    print(f"═══ 账户概览 ═══")
    print(f"  总资产: ¥{total_assets:,.2f}")
    print(f"  可用资金: ¥{p['total_cash']:,.2f}")
    print(f"  持仓市值: ¥{market_value:,.2f}")
    print(f"  总盈亏: {sign}¥{total_pnl:,.2f} ({sign}{total_pnl_pct:.2f}%)")
    print(f"  初始资金: ¥{p['initial_capital']:,.2f}")
    print()

    if pos_details:
        print(f"═══ 持仓明细 ═══")
        for d in pos_details:
            s = '+' if d['pnl'] >= 0 else ''
            arrow = '🟢' if d['pnl'] >= 0 else '🔴'
            print(f"  {arrow} {d['name']} ({d['code']})")
            print(f"     {d['shares']}股 | 成本 {d['avg_cost']:.2f} | 现价 {d['current_price']:.2f}")
            print(f"     市值 ¥{d['market_value']:,.2f} | 盈亏 {s}¥{d['pnl']:,.2f} ({s}{d['pnl_pct']:.2f}%)")
        print()

    # 仓位分布
    if pos_details and total_assets > 0:
        print(f"═══ 仓位分布 ═══")
        cash_pct = p["total_cash"] / total_assets * 100
        print(f"  现金: {cash_pct:.1f}%")
        for d in pos_details:
            pct = d["market_value"] / total_assets * 100
            print(f"  {d['name']}: {pct:.1f}%")

def cmd_trades(args):
    """查看交易流水"""
    trades = _get_trades()
    if not trades:
        print("暂无交易记录")
        return

    limit = args.limit or 20
    recent = trades[-limit:]

    if args.json:
        print(json.dumps(recent, ensure_ascii=False, indent=2))
        return

    print(f"═══ 最近 {len(recent)} 条交易记录 ═══\n")
    for t in recent:
        action_map = {"init": "初始化", "deposit": "转入", "withdraw": "转出", "buy": "买入", "sell": "卖出"}
        action = action_map.get(t["action"], t["action"])
        if t["action"] in ("buy", "sell"):
            print(f"  {t['time']} | {action} {t['name']}({t['code']}) {t['shares']}股 × ¥{t['price']:.2f}")
            if t.get("note"):
                print(f"    {t['note']}")
        else:
            print(f"  {t['time']} | {action} ¥{abs(t['amount']):,.2f}  {t.get('note', '')}")

# ── Main ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="资金仓位管理")
    sub = parser.add_subparsers(dest="command")

    # init
    p = sub.add_parser("init", help="初始化账户")
    p.add_argument("--capital", type=float, required=True, help="初始资金")

    # deposit
    p = sub.add_parser("deposit", help="转入资金")
    p.add_argument("--amount", type=float, required=True)
    p.add_argument("--note", default="")

    # withdraw
    p = sub.add_parser("withdraw", help="转出资金")
    p.add_argument("--amount", type=float, required=True)
    p.add_argument("--note", default="")

    # buy
    p = sub.add_parser("buy", help="买入股票")
    p.add_argument("--code", required=True, help="股票代码")
    p.add_argument("--name", default="", help="股票名称")
    p.add_argument("--shares", type=int, required=True, help="股数")
    p.add_argument("--price", type=float, required=True, help="买入价")

    # sell
    p = sub.add_parser("sell", help="卖出股票")
    p.add_argument("--code", required=True, help="股票代码")
    p.add_argument("--shares", type=int, required=True, help="股数")
    p.add_argument("--price", type=float, required=True, help="卖出价")

    # status
    p = sub.add_parser("status", help="账户状态")
    p.add_argument("--json", action="store_true")

    # trades
    p = sub.add_parser("trades", help="交易流水")
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--json", action="store_true")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    cmds = {
        "init": cmd_init, "deposit": cmd_deposit, "withdraw": cmd_withdraw,
        "buy": cmd_buy, "sell": cmd_sell, "status": cmd_status, "trades": cmd_trades,
    }
    cmds[args.command](args)

if __name__ == "__main__":
    main()
