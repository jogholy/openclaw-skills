"""
Stock Analysis Library - A comprehensive technical analysis toolkit for stock market data.

This library provides modules for:
- Technical indicator calculations
- Signal generation
- Backtesting strategies
- Data processing and validation
"""

__version__ = "1.0.0"
__author__ = "Stock Analysis Library"

from . import indicators
from . import signals
from . import backtest
from . import data

__all__ = ['indicators', 'signals', 'backtest', 'data']