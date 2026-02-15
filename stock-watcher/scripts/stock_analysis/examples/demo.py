"""
Stock Analysis Library Demo

This script demonstrates the usage of the stock analysis library with a complete example.
It shows how to:
1. Load and preprocess financial data
2. Calculate technical indicators
3. Generate trading signals
4. Run a backtest
5. Analyze results
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# Add the parent directory to the path to import the library
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from stock_analysis import indicators, signals, backtest, data


def generate_sample_data(days: int = 252) -> pd.DataFrame:
    """
    Generate sample financial data for demonstration purposes.
    
    Args:
        days: Number of days of data to generate
        
    Returns:
        DataFrame with OHLCV data
    """
    np.random.seed(42)  # For reproducible results
    
    # Generate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    dates = pd.date_range(start=start_date, end=end_date, freq='D')
    
    # Start with a base price
    base_price = 100.0
    prices = [base_price]
    
    # Generate random returns (daily)
    returns = np.random.normal(0.0005, 0.02, days)  # Mean 0.05%, std 2%
    
    for ret in returns:
        new_price = prices[-1] * (1 + ret)
        prices.append(new_price)
    
    # Create OHLC data with some variation
    closes = prices[1:]  # Remove initial base price
    opens = [prices[0]] + closes[:-1]  # Open is previous close
    
    # Generate high, low, and adjusted close with some variation
    highs = []
    lows = []
    
    for i in range(len(closes)):
        # High is close + random positive variation
        high_variation = abs(np.random.normal(0, 0.01))  # 1% average variation
        high = closes[i] * (1 + high_variation)
        
        # Low is close - random positive variation  
        low_variation = abs(np.random.normal(0, 0.01))  # 1% average variation
        low = closes[i] * (1 - low_variation)
        
        highs.append(high)
        lows.append(max(low, 0.1))  # Ensure positive low values
    
    # Generate volume data
    volumes = np.random.uniform(1000000, 5000000, len(dates))  # Random volume
    
    # Create DataFrame
    df = pd.DataFrame({
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': volumes
    }, index=dates)
    
    return df


def demonstrate_indicators():
    """Demonstrate the technical indicators module."""
    print("=" * 60)
    print("DEMONSTRATING TECHNICAL INDICATORS")
    print("=" * 60)
    
    # Generate sample data
    sample_data = generate_sample_data(100)
    prices = sample_data['close']
    
    print(f"Generated {len(sample_data)} days of sample data")
    print(f"Price range: ${prices.min():.2f} - ${prices.max():.2f}")
    print()
    
    # Calculate Moving Averages
    print("1. MOVING AVERAGES")
    ma_system = indicators.ma_system(prices)
    for ma_period in [5, 10, 20, 60]:
        ma_val = ma_system[f'MA{ma_period}'].iloc[-1]
        current_price = prices.iloc[-1]
        print(f"   MA{ma_period}: ${ma_val:.2f} (Price: ${current_price:.2f})")
    print()
    
    # Calculate MACD
    print("2. MACD (Moving Average Convergence Divergence)")
    macd_line, signal_line, histogram = indicators.macd(prices)
    print(f"   MACD Line: {macd_line.iloc[-1]:.4f}")
    print(f"   Signal Line: {signal_line.iloc[-1]:.4f}")
    print(f"   Histogram: {histogram.iloc[-1]:.4f}")
    print()
    
    # Calculate RSI
    print("3. RSI (Relative Strength Index)")
    rsi = indicators.rsi(prices)
    print(f"   RSI: {rsi.iloc[-1]:.2f}")
    print(f"   Status: {'Overbought' if rsi.iloc[-1] > 70 else 'Oversold' if rsi.iloc[-1] < 30 else 'Neutral'}")
    print()
    
    # Calculate Bollinger Bands
    print("4. BOLLINGER BANDS")
    upper, middle, lower = indicators.bollinger_bands(prices)
    current_price = prices.iloc[-1]
    print(f"   Upper Band: ${upper.iloc[-1]:.2f}")
    print(f"   Middle Band: ${middle.iloc[-1]:.2f}")
    print(f"   Lower Band: ${lower.iloc[-1]:.2f}")
    print(f"   Current Price: ${current_price:.2f}")
    print(f"   Position: {(current_price - lower.iloc[-1]) / (upper.iloc[-1] - lower.iloc[-1]):.2%} between bands")
    print()
    
    # Calculate KDJ
    print("5. STOCHASTIC OSCILLATOR (KDJ)")
    k, d, j = indicators.kdj(sample_data['high'], sample_data['low'], sample_data['close'])
    print(f"   %K: {k.iloc[-1]:.2f}")
    print(f"   %D: {d.iloc[-1]:.2f}")
    print(f"   %J: {j.iloc[-1]:.2f}")
    print()
    
    # Calculate Volume Indicators
    print("6. VOLUME INDICATORS")
    obv = indicators.obv(sample_data['close'], sample_data['volume'])
    vol_ma = indicators.volume_ma(sample_data['volume'])
    print(f"   OBV: {obv.iloc[-1]:.0f}")
    print(f"   Volume MA: {vol_ma.iloc[-1]:.0f}")
    print()


def demonstrate_signals():
    """Demonstrate the signals module."""
    print("=" * 60)
    print("DEMONSTRATING SIGNAL GENERATION")
    print("=" * 60)
    
    # Generate sample data
    sample_data = generate_sample_data(100)
    
    # Calculate indicators
    close_prices = sample_data['close']
    ma_fast = indicators.moving_average(close_prices, 5)
    ma_slow = indicators.moving_average(close_prices, 20)
    rsi = indicators.rsi(close_prices)
    
    # Generate signals
    print("1. GOLDEN/DEATH CROSS SIGNALS")
    cross_signals = signals.golden_death_cross(ma_fast, ma_slow)
    recent_cross_signal = cross_signals.iloc[-5:]  # Last 5 signals
    for date, signal in recent_cross_signal.items():
        signal_desc = "Golden Cross (BUY)" if signal == 1 else "Death Cross (SELL)" if signal == -1 else "No Signal"
        print(f"   {date.strftime('%Y-%m-%d')}: {signal_desc}")
    print()
    
    print("2. OVERSOLD/OVERBOUGHT SIGNALS (based on RSI)")
    os_ob_signals = signals.oversold_overbought(rsi)
    recent_os_ob = os_ob_signals.iloc[-5:]  # Last 5 signals
    for date, signal in recent_os_ob.items():
        signal_desc = "Oversold (BUY)" if signal == 1 else "Overbought (SELL)" if signal == -1 else "Neutral"
        print(f"   {date.strftime('%Y-%m-%d')}: {signal_desc}")
    print()
    
    print("3. TREND STRENGTH")
    trend_strength = signals.trend_strength(close_prices)
    print(f"   Current trend strength: {trend_strength.iloc[-1]:.4f}")
    print(f"   Interpretation: {'Strong Uptrend' if trend_strength.iloc[-1] > 0.5 else 'Strong Downtrend' if trend_strength.iloc[-1] < -0.5 else 'Weak Trend'}")
    print()
    
    print("4. COMBINED SIGNALS")
    combined_signals_df = signals.combined_signals(sample_data)
    latest_signals = combined_signals_df.iloc[-1]
    print(f"   MA Signal: {latest_signals['ma_signal']}")
    print(f"   RSI Signal: {latest_signals['rsi_signal']}")
    print(f"   BB Position: {latest_signals['bb_position']:.3f}")
    print(f"   Composite Score: {latest_signals['composite_score']:.3f}")
    print()
    
    print("5. FINAL TRADING SIGNALS (Moderate Strategy)")
    final_signals = signals.generate_trading_signals(combined_signals_df, strategy='moderate')
    recent_final_signals = final_signals.iloc[-5:]  # Last 5 signals
    for date, signal in recent_final_signals.items():
        signal_desc = "BUY" if signal == 1 else "SELL" if signal == -1 else "HOLD"
        print(f"   {date.strftime('%Y-%m-%d')}: {signal_desc}")
    print()


def demonstrate_backtesting():
    """Demonstrate the backtesting module."""
    print("=" * 60)
    print("DEMONSTRATING BACKTESTING")
    print("=" * 60)
    
    # Generate more data for backtesting (1 year)
    sample_data = generate_sample_data(252)
    
    # Calculate signals for the entire period
    combined_signals_df = signals.combined_signals(sample_data)
    final_signals = signals.generate_trading_signals(combined_signals_df, strategy='moderate')
    
    # Create and run backtest
    bt_engine = backtest.BacktestEngine(initial_capital=100000)
    results = bt_engine.run_backtest(
        data=sample_data,
        signals=final_signals,
        position_size=0.1,  # 10% position size
        transaction_cost=0.001  # 0.1% transaction cost
    )
    
    # Print results
    print("BACKTEST RESULTS:")
    print(f"   Initial Capital: ${results['initial_capital']:,.2f}")
    print(f"   Final Capital: ${results['final_capital']:,.2f}")
    print(f"   Total Return: {results['total_return']:.2%}")
    print(f"   Annual Return: {results['annual_return']:.2%}")
    print(f"   Max Drawdown: {results['max_drawdown']:.2%}")
    print(f"   Sharpe Ratio: {results['sharpe_ratio']:.2f}")
    print(f"   Sortino Ratio: {results['sortino_ratio']:.2f}")
    print(f"   Win Rate: {results['win_rate']:.2%}")
    print(f"   Total Trades: {results['total_trades']}")
    print(f"   Period: {results['start_date'].strftime('%Y-%m-%d')} to {results['end_date'].strftime('%Y-%m-%d')}")
    print()
    
    print("PERFORMANCE SUMMARY:")
    print(bt_engine.get_performance_summary())


def demonstrate_data_processing():
    """Demonstrate the data processing module."""
    print("=" * 60)
    print("DEMONSTRATING DATA PROCESSING")
    print("=" * 60)
    
    # Generate sample data with some issues
    sample_data = generate_sample_data(50)
    
    # Introduce some missing values
    corrupted_data = sample_data.copy()
    corrupted_data.loc[corrupted_data.index[5:7], 'volume'] = np.nan
    corrupted_data.loc[corrupted_data.index[10], 'close'] = np.nan
    
    print("1. DATA VALIDATION")
    try:
        data.validate_ohlcv(corrupted_data)
        print("   Data is valid")
    except ValueError as e:
        print(f"   Validation error: {e}")
    print()
    
    print("2. CLEANING MISSING VALUES")
    print(f"   Original missing values: {corrupted_data.isnull().sum().sum()}")
    cleaned_data = data.clean_missing_values(corrupted_data, method='interpolate')
    print(f"   After cleaning: {cleaned_data.isnull().sum().sum()} missing values")
    print()
    
    print("3. RESAMPLING DATA")
    monthly_data = data.resample_data(sample_data, timeframe='1M')
    print(f"   Original data points: {len(sample_data)}")
    print(f"   Monthly data points: {len(monthly_data)}")
    print()
    
    print("4. OUTLIER DETECTION")
    # Add an artificial outlier
    outlier_data = sample_data.copy()
    outlier_data.loc[outlier_data.index[20], 'close'] = sample_data['close'].mean() * 2  # Artificially high
    outliers = data.detect_outliers(outlier_data['close'], method='iqr')
    print(f"   Outliers detected: {outliers.sum()}")
    print(f"   Dates with outliers: {outlier_data[outliers].index.tolist()}")
    print()
    
    print("5. RETURN CALCULATIONS")
    returns = data.calculate_returns(sample_data['close'], method='simple')
    cumulative_returns = data.calculate_cumulative_returns(returns)
    print(f"   Latest simple return: {returns.iloc[-1]:.4f}")
    print(f"   Latest cumulative return: {cumulative_returns.iloc[-1]:.4f}")


def main():
    """Main function to run all demonstrations."""
    print("STOCK ANALYSIS LIBRARY DEMONSTRATION")
    print("This script demonstrates the key features of the stock analysis library.\n")
    
    try:
        demonstrate_data_processing()
        demonstrate_indicators()
        demonstrate_signals()
        demonstrate_backtesting()
        
        print("\n" + "=" * 60)
        print("DEMONSTRATION COMPLETE!")
        print("=" * 60)
        print("\nThe stock analysis library provides a comprehensive set of tools for:")
        print("- Technical indicator calculations")
        print("- Signal generation and analysis") 
        print("- Strategy backtesting and evaluation")
        print("- Financial data processing and validation")
        print("\nAll components work together to enable systematic analysis of stock market data.")
        
    except Exception as e:
        print(f"An error occurred during the demonstration: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()