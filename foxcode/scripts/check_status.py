#!/usr/bin/env python3
"""
FoxCode Server Status Checker
Parses preloadData JSON embedded in https://status.rjj.cc/status/foxcode
Then fetches heartbeat data per monitor for uptime %.
"""

import json
import re
import sys
import urllib.request
import urllib.error
import argparse

STATUS_URL = "https://status.rjj.cc/status/foxcode"
# Upkuma API for heartbeat data (24h range)
HEARTBEAT_URL = "https://status.rjj.cc/api/status-page/heartbeat/foxcode"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"


def fetch_page():
    """Fetch the status page HTML."""
    req = urllib.request.Request(STATUS_URL, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8")


def fetch_heartbeats():
    """Fetch heartbeat data from API."""
    req = urllib.request.Request(HEARTBEAT_URL, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def parse_preload(html):
    """Extract preloadData from the embedded script tag.
    The data is JS object literal (single quotes, null/true/false), not JSON.
    Convert to valid JSON before parsing.
    """
    m = re.search(r"window\.preloadData\s*=\s*(\{.+?\});\s*<", html, re.DOTALL)
    if not m:
        return None
    raw = m.group(1)
    # Convert JS object to JSON: replace single quotes with double quotes,
    # handle null/true/false (already valid JSON keywords)
    # Use a simple approach: replace ' with " but handle escaped quotes
    converted = raw.replace("'", '"')
    try:
        return json.loads(converted)
    except json.JSONDecodeError:
        return None


def compute_uptime(heartbeat_list):
    """Compute uptime % from a list of heartbeat entries."""
    if not heartbeat_list:
        return None
    up = sum(1 for h in heartbeat_list if h.get("status") == 1)
    return round(up / len(heartbeat_list) * 100, 2)


def get_status():
    """Get full status information."""
    html = fetch_page()
    data = parse_preload(html)
    if not data:
        return {"error": "无法解析状态数据", "url": STATUS_URL}

    config = data.get("config", {})
    groups = data.get("publicGroupList", [])

    # Fetch heartbeat data for uptime %
    hb_data = fetch_heartbeats()
    heartbeats = {}
    uptimes = {}
    if hb_data and "heartbeatList" in hb_data:
        heartbeats = hb_data["heartbeatList"]
    if hb_data and "uptimeList" in hb_data:
        uptimes = hb_data["uptimeList"]

    result = {
        "title": config.get("title", "FoxCode"),
        "url": STATUS_URL,
        "groups": [],
    }

    all_up = True
    any_down = False

    for group in groups:
        g = {"name": group["name"], "monitors": []}
        for mon in group.get("monitorList", []):
            mid = str(mon["id"])
            # Get uptime from uptimeList (key format: "id_24")
            uptime_key_24 = f"{mid}_24"
            uptime_pct = uptimes.get(uptime_key_24)
            if uptime_pct is not None:
                uptime_pct = round(float(uptime_pct) * 100, 2)

            # Get latest status from heartbeat list
            hb_list = heartbeats.get(mid, [])
            latest_status = None
            if hb_list:
                latest = hb_list[-1] if isinstance(hb_list, list) else None
                if latest:
                    latest_status = "up" if latest.get("status") == 1 else "down"

            if latest_status != "up":
                all_up = False
            if latest_status == "down":
                any_down = True

            g["monitors"].append({
                "name": mon["name"],
                "type": mon.get("type", "unknown"),
                "status": latest_status or "unknown",
                "uptime_24h": uptime_pct,
            })
        result["groups"].append(g)

    if all_up:
        result["overall"] = "正常"
    elif any_down:
        result["overall"] = "部分服务降级"
    else:
        result["overall"] = "未知"

    return result


def format_output(data):
    """Format status data for human-readable output."""
    if "error" in data:
        return f"❌ {data['error']}\n状态页面: {data['url']}"

    lines = [f"FoxCode 状态: {data['overall']}"]
    lines.append("")

    for group in data["groups"]:
        lines.append(f"【{group['name']}】")
        for mon in group["monitors"]:
            icon = "✅" if mon["status"] == "up" else "❌" if mon["status"] == "down" else "❓"
            uptime = f"{mon['uptime_24h']}%" if mon["uptime_24h"] is not None else "N/A"
            lines.append(f"  {icon} {mon['name']}: {uptime}")
        lines.append("")

    lines.append(f"状态页面: {data['url']}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="查询 FoxCode 服务器状态")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    args = parser.parse_args()

    try:
        data = get_status()
    except Exception as e:
        data = {"error": str(e), "url": STATUS_URL}

    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(format_output(data))


if __name__ == "__main__":
    main()
