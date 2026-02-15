# Stock Analysis Library

A comprehensive Python library for stock market technical analysis, signal generation, and strategy backtesting.

## Overview

The Stock Analysis Library provides a complete toolkit for analyzing stock market data using technical indicators. It includes modules for:

- **Technical Indicator Calculations**: MACD, RSI, Bollinger Bands, KDJ, Moving Averages, Volume indicators
- **Signal Generation**: Golden/Death cross detection, Overbought/Oversold identification, Trend analysis
- **Backtesting Engine**: Strategy testing with performance metrics
- **Data Processing**: Data validation, cleaning, and transformation

## Installation

```bash
pip install -r requirements.txt
```

## Quick Start

Here's a quick example to get you started:

```python
import pandas as pd
from stock_analysis import indicators, signals, backtest

# Load your data (OHLCV format)
data = pd.read_csv('your_stock_data.csv', index_col='date', parse_dates=True)

# Calculate technical indicators
rsi = indicators.rsi(data['close'])
macd_line, signal_line, histogram = indicators.macd(data['close'])

# Generate trading signals
combined_signals = signals.combined_signals(data)
final_signals = signals.generate_trading_signals(combined_signals, strategy='moderate')

# Run backtest
bt = backtest.BacktestEngine(initial_capital=100000)
results = bt.run_backtest(data, final_signals)
print(bt.get_performance_summary())
```

## Features

### Technical Indicators
- **MACD**: Moving Average Convergence Divergence
- **RSI**: Relative Strength Index  
- **Bollinger Bands**: Volatility-based price channels
- **KDJ**: Stochastic oscillator
- **Moving Averages**: MA5, MA10, MA20, MA60
- **Volume Indicators**: OBV, Volume Moving Average

### Signal Generation
- Golden Cross / Death Cross detection
- Overbought / Oversold conditions
- Trend strength analysis
- Multi-indicator combined signals
- Configurable trading strategies

### Backtesting
- Portfolio simulation
- Performance metrics (returns, drawdown, Sharpe ratio)
- Risk-adjusted returns
- Trade history tracking

### Data Processing
- OHLCV data validation
- Missing value handling
- Outlier detection and removal
- Data resampling
- Return calculations

## Usage Examples

For complete usage examples, see the [examples/demo.py](examples/demo.py) file which demonstrates:

1. Loading and preprocessing financial data
2. Calculating technical indicators
3. Generating trading signals
4. Running a backtest
5. Analyzing results

## Project Structure

```
stock_analysis/
├── __init__.py
├── indicators.py          # Technical indicator calculations
├── signals.py             # Signal generation
├── backtest.py           # Backtesting engine
├── data.py               # Data processing utilities
├── tests/
│   ├── __init__.py
│   ├── test_indicators.py
│   └── test_signals.py
├── examples/
│   └── demo.py           # Complete usage example
├── README.md
└── requirements.txt
```

## Testing

Run the unit tests to verify the library works correctly:

```bash
python -m pytest stock_analysis/tests/
```

Or run individual test files:

```bash
python -m stock_analysis.tests.test_indicators
python -m stock_analysis.tests.test_signals
```

## Requirements

- Python 3.7+
- numpy
- pandas
- matplotlib (for visualization)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This library is for educational and research purposes only. Past performance does not guarantee future results. Always do your own research and consider consulting with a qualified financial advisor before making investment decisions.