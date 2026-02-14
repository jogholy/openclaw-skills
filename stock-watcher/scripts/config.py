#!/usr/bin/env python3
"""
Configuration for stock-watcher skill.
Centralized configuration to avoid path confusion.
"""
import os

# 数据目录
DATA_DIR = os.path.expanduser("~/.clawdbot/stock_watcher")
WATCHLIST_FILE = os.path.join(DATA_DIR, "watchlist.txt")
PORTFOLIO_FILE = os.path.join(DATA_DIR, "portfolio.json")
TRADES_FILE = os.path.join(DATA_DIR, "trades.json")

# 兼容旧变量名
WATCHLIST_DIR = DATA_DIR

# Ensure directory exists
os.makedirs(DATA_DIR, exist_ok=True)
