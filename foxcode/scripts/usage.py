#!/usr/bin/env python3
"""
FoxCode Usage - Query quota and usage from foxcode.rjj.cc
Pure Python stdlib, no external dependencies.
"""

import json
import os
import sys
import time
import urllib.request
import urllib.parse
import urllib.error
import argparse
from datetime import datetime, timezone, timedelta

BASE_URL = "https://foxcode.rjj.cc"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
CONFIG_FILE = os.path.join(SKILL_DIR, "config.json")
TOKEN_FILE = os.path.join(SKILL_DIR, "data", "token.json")

CST = timezone(timedelta(hours=8))


class FoxCodeAPI:
    def __init__(self):
        self.token = None
        self.load_token()

    def load_config(self):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Error: {CONFIG_FILE} not found", file=sys.stderr)
            sys.exit(1)

    def load_token(self):
        try:
            with open(TOKEN_FILE, 'r') as f:
                d = json.load(f)
                if d.get('exp', 0) > time.time():
                    self.token = d['token']
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            pass

    def save_token(self, token, exp_time):
        os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
        with open(TOKEN_FILE, 'w') as f:
            json.dump({'token': token, 'exp': exp_time}, f)
        self.token = token

    def login(self):
        cfg = self.load_config()
        body = json.dumps({'email': cfg['email'], 'password': cfg['password']}).encode()
        req = urllib.request.Request(
            f"{BASE_URL}/api/auth/login",
            data=body,
            headers={'Content-Type': 'application/json', 'User-Agent': UA},
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read())
                token = result.get('data', {}).get('token') or result.get('token')
                if not token:
                    # Try reading from Set-Cookie
                    cookie = resp.headers.get('Set-Cookie', '')
                    for part in cookie.split(';'):
                        if 'auth_token=' in part:
                            token = part.split('auth_token=')[1].strip()
                            break
                if token:
                    # JWT exp is 7 days, cache for 6 days
                    self.save_token(token, time.time() + 6 * 86400)
                    return True
                print("Login failed: no token in response", file=sys.stderr)
                return False
        except urllib.error.HTTPError as e:
            body_text = e.read().decode('utf-8', errors='replace')
            print(f"Login failed: HTTP {e.code} - {body_text[:200]}", file=sys.stderr)
            return False

    def ensure_auth(self):
        if not self.token:
            if not self.login():
                sys.exit(1)

    def get(self, endpoint, params=None):
        self.ensure_auth()
        url = f"{BASE_URL}{endpoint}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={'Authorization': f'Bearer {self.token}', 'User-Agent': UA})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code == 401:
                self.token = None
                if self.login():
                    return self.get(endpoint, params)
                print("Auth failed", file=sys.stderr)
                sys.exit(1)
            body_text = e.read().decode('utf-8', errors='replace')
            print(f"API error: HTTP {e.code} - {body_text[:200]}", file=sys.stderr)
            sys.exit(1)


def fmt_num(n):
    if n is None:
        return "N/A"
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.2f}B"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.2f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(int(n))


def fmt_cost(quota_cost):
    """Convert quota cost units to approximate USD (quota units ≈ $1/M)"""
    return f"${quota_cost / 1_000_000:.4f}" if quota_cost else "$0"


def fmt_time(iso_str):
    try:
        dt = datetime.fromisoformat(iso_str.replace('Z', '+00:00')).astimezone(CST)
        return dt.strftime('%m-%d %H:%M')
    except Exception:
        return iso_str[:16] if iso_str else 'N/A'


# ── Commands ──────────────────────────────────────────────

def cmd_quota(api, args):
    resp = api.get("/api/user/dashboard")
    if args.json:
        print(json.dumps(resp, indent=2, ensure_ascii=False))
        return
    d = resp.get('data', resp)
    q = d.get('quota', {})
    remaining = q.get('quotaRemaining', 0)
    limit = q.get('quotaLimit', 0)
    used = q.get('currentUsage', 0)
    pct = q.get('usagePercentage', 0)
    print(f"剩余: {fmt_num(remaining)} / {fmt_num(limit)}  (已用 {pct:.1f}%)")


def cmd_status(api, args):
    dashboard = api.get("/api/user/dashboard")
    multiplier = api.get("/api/user/quota/multiplier")
    stats = api.get("/api/user/quota/usage-statistics")

    if args.json:
        print(json.dumps({'dashboard': dashboard, 'multiplier': multiplier, 'statistics': stats}, indent=2, ensure_ascii=False))
        return

    d = dashboard.get('data', dashboard)
    q = d.get('quota', {})
    remaining = q.get('quotaRemaining', 0)
    limit = q.get('quotaLimit', 0)
    pct = q.get('usagePercentage', 0)

    print("═══ 额度总览 ═══")
    print(f"剩余: {fmt_num(remaining)} / {fmt_num(limit)}  ({pct:.1f}% 已用)")

    # 套餐明细
    breakdown = q.get('subscriptionBreakdown', [])
    if breakdown:
        print("\n═══ 套餐明细 ═══")
        for sub in breakdown:
            name = sub.get('planName', '?')
            used = sub.get('used', 0)
            lim = sub.get('limit', 0)
            rem = sub.get('remaining', 0)
            sub_pct = sub.get('usagePercentage', 0)
            print(f"  {name}: {fmt_num(rem)} 剩余 / {fmt_num(lim)} ({sub_pct:.1f}% 已用)")

    # 倍率
    m = multiplier.get('data', multiplier)
    rate = m.get('multiplier', 1.0)
    print(f"\n═══ 当前倍率 ═══\n  {rate}x")

    # 模型用量
    s = stats.get('data', stats)
    models = s.get('statistics', {}).get('modelBreakdown', [])
    if models:
        print("\n═══ 模型用量 ═══")
        for mod in models:
            name = mod.get('model', '?')
            calls = mod.get('requestCount', 0)
            tokens = mod.get('totalTokens', 0)
            cost = mod.get('quotaCost', 0)
            print(f"  {name}")
            print(f"    {calls} 次调用 | {fmt_num(tokens)} tokens | 额度 {fmt_num(cost)}")


def cmd_models(api, args):
    params = {}
    if hasattr(args, 'date') and args.date:
        params['startDate'] = args.date
        params['endDate'] = args.date
    resp = api.get("/api/user/quota/usage-statistics", params if params else None)
    if args.json:
        print(json.dumps(resp, indent=2, ensure_ascii=False))
        return
    s = resp.get('data', resp)
    models = s.get('statistics', {}).get('modelBreakdown', [])
    if not models:
        print("暂无用量数据")
        return
    label = f" ({args.date})" if hasattr(args, 'date') and args.date else ""
    print(f"═══ 模型用量分布{label} ═══")
    total_cost = sum(m.get('quotaCost', 0) for m in models)
    for mod in models:
        name = mod.get('model', '?')
        calls = mod.get('requestCount', 0)
        tokens = mod.get('totalTokens', 0)
        cost = mod.get('quotaCost', 0)
        share = (cost / total_cost * 100) if total_cost else 0
        print(f"\n  {name}")
        print(f"    调用: {calls} 次")
        print(f"    Tokens: {fmt_num(tokens)}")
        print(f"    额度消耗: {fmt_num(cost)} ({share:.1f}%)")


def cmd_trend(api, args):
    resp = api.get("/api/user/quota/usage-chart")
    if args.json:
        print(json.dumps(resp, indent=2, ensure_ascii=False))
        return
    d = resp.get('data', resp)
    total = d.get('total', [])
    models_data = d.get('models', {})
    model_list = d.get('modelList', [])

    # Filter by model
    if args.model:
        matched = None
        for m in model_list:
            if args.model.lower() in m.lower():
                matched = m
                break
        if matched and matched in models_data:
            print(f"═══ 24h 趋势: {matched} ═══")
            entries = models_data[matched]
        else:
            print(f"模型 '{args.model}' 未找到，可选: {', '.join(model_list)}")
            return
    else:
        print("═══ 24h 总趋势 ═══")
        entries = total

    nonzero = [e for e in entries if e.get('totalCalls', 0) > 0]
    if not nonzero:
        print("最近 24h 无调用")
        return

    print(f"{'时段':>6} | {'调用':>6} | {'额度消耗':>10}")
    print("-" * 32)
    for e in nonzero:
        hour = e.get('displayHour', '?')
        calls = e.get('totalCalls', 0)
        cost = e.get('totalCost', 0)
        print(f"  {hour:02d}:00 | {calls:>6} | {fmt_num(cost):>10}")


def cmd_records(api, args):
    params = {'page': args.page, 'pageSize': args.size}
    if args.model:
        params['model'] = args.model
    resp = api.get("/api/user/quota/usage", params)
    if args.json:
        print(json.dumps(resp, indent=2, ensure_ascii=False))
        return
    d = resp.get('data', resp)
    records = d.get('records', [])
    pag = d.get('pagination', {})
    total = pag.get('total', 0)
    page = pag.get('page', args.page)

    print(f"═══ 消费明细 (第{page}页, 共{total}条) ═══\n")
    if not records:
        print("暂无记录")
        return

    for r in records:
        ts = fmt_time(r.get('createdAt', ''))
        model = r.get('model', '?')
        in_tok = r.get('inputTokens', 0)
        out_tok = r.get('outputTokens', 0)
        cache_w = r.get('cacheCreationInputTokens', 0)
        cache_r = r.get('cacheReadInputTokens', 0)
        cost = r.get('quotaCost', 0)
        print(f"  {ts} | {model}")
        parts = [f"in:{fmt_num(in_tok)}", f"out:{fmt_num(out_tok)}"]
        if cache_w:
            parts.append(f"cache_w:{fmt_num(cache_w)}")
        if cache_r:
            parts.append(f"cache_r:{fmt_num(cache_r)}")
        parts.append(f"额度:{fmt_num(cost)}")
        print(f"    {' | '.join(parts)}")


def cmd_login(api, args):
    api.token = None
    if api.login():
        print("登录成功 ✅")
    else:
        print("登录失败 ❌")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="FoxCode 额度用量查询")
    sub = parser.add_subparsers(dest='command')

    for name, hlp in [('quota', '快速查额度'), ('status', '完整状态'), ('models', '模型用量'),
                       ('trend', '24h趋势'), ('records', '消费明细'), ('login', '刷新登录')]:
        p = sub.add_parser(name, help=hlp)
        p.add_argument('--json', action='store_true', help='输出原始 JSON')
        if name in ('models', 'status'):
            p.add_argument('--date', help='指定日期 (YYYY-MM-DD)')
        if name == 'trend':
            p.add_argument('--model', help='按模型筛选')
        if name == 'records':
            p.add_argument('--page', type=int, default=1, help='页码')
            p.add_argument('--size', type=int, default=10, help='每页条数')
            p.add_argument('--model', help='按模型筛选')

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    api = FoxCodeAPI()
    cmds = {
        'quota': cmd_quota, 'status': cmd_status, 'models': cmd_models,
        'trend': cmd_trend, 'records': cmd_records, 'login': cmd_login,
    }
    cmds[args.command](api, args)


if __name__ == '__main__':
    main()
