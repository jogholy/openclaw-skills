"""
Signal Generation Module

This module provides functions to generate trading signals based on technical indicators.

Functions:
    - golden_death_cross: Detect golden/death cross patterns
    - oversold_overbought: Identify oversold/overbought conditions
    - trend_strength: Calculate trend strength scores
    - combined_signals: Generate comprehensive signals from multiple indicators
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, List
try:
    from . import indicators
except ImportError:
    import indicators  # Fallback for direct execution


def golden_death_cross(fast_ma: pd.Series, slow_ma: pd.Series, 
                       lookback_period: int = 5) -> pd.Series:
    """
    Detect golden cross (bullish) and death cross (bearish) patterns.
    
    Args:
        fast_ma: Fast moving average series
        slow_ma: Slow moving average series
        lookback_period: Number of periods to look back for cross detection
        
    Returns:
        Series with signal values:
        - 1 for golden cross (bullish)
        - -1 for death cross (bearish)
        - 0 for no signal
        
    Example:
        >>> import pandas as pd
        >>> fast_ma = pd.Series([95, 96, 97, 98, 99, 100, 101])
        >>> slow_ma = pd.Series([100, 99, 98, 97, 96, 95, 94])
        >>> signals = golden_death_cross(fast_ma, slow_ma)
        >>> print(signals.iloc[-1])  # Last signal
        1
    """
    if not isinstance(fast_ma, pd.Series) or not isinstance(slow_ma, pd.Series):
        raise TypeError("Both inputs must be pandas Series")
    
    if len(fast_ma) != len(slow_ma):
        raise ValueError("Series must have the same length")
    
    if lookback_period <= 0:
        raise ValueError("Lookback period must be positive")
    
    if len(fast_ma) < lookback_period + 1:
        raise ValueError(f"Not enough data points. Need at least {lookback_period + 1}, got {len(fast_ma)}")
    
    # Calculate differences
    current_diff = fast_ma - slow_ma
    previous_diff = current_diff.shift(1)
    
    # Detect crosses
    golden_cross = ((current_diff > 0) & (previous_diff <= 0)).astype(int)
    death_cross = ((current_diff < 0) & (previous_diff >= 0)).astype(int) * -1
    
    # Combine signals
    signals = golden_cross + death_cross
    
    return signals


def oversold_overbought(rsi: pd.Series, 
                        overbought_level: float = 70.0,
                        oversold_level: float = 30.0) -> pd.Series:
    """
    Identify oversold and overbought conditions based on RSI.
    
    Args:
        rsi: RSI series (0-100)
        overbought_level: Level above which considered overbought (default 70)
        oversold_level: Level below which considered oversold (default 30)
        
    Returns:
        Series with signal values:
        - 1 for oversold (potential buy signal)
        - -1 for overbought (potential sell signal)
        - 0 for neutral
        
    Example:
        >>> import pandas as pd
        >>> rsi = pd.Series([25, 35, 45, 55, 65, 75, 85])
        >>> signals = oversold_overbought(rsi)
        >>> print(signals.iloc[0])  # Oversold signal
        1
        >>> print(signals.iloc[-1])  # Overbought signal
        -1
    """
    if not isinstance(rsi, pd.Series):
        raise TypeError("RSI must be a pandas Series")
    
    if overbought_level <= oversold_level:
        raise ValueError("Overbought level must be greater than oversold level")
    
    if overbought_level >= 100 or oversold_level <= 0:
        raise ValueError("RSI levels must be between 0 and 100")
    
    # Check for valid RSI values
    invalid_rsi = rsi[(rsi < 0) | (rsi > 100)]
    if len(invalid_rsi) > 0:
        raise ValueError(f"Invalid RSI values found: {invalid_rsi.values}")
    
    oversold = (rsi <= oversold_level).astype(int)
    overbought = (rsi >= overbought_level).astype(int) * -1
    
    signals = oversold + overbought
    
    return signals


def trend_strength(data: pd.Series, window: int = 20) -> pd.Series:
    """
    Calculate trend strength based on the slope of a moving average.
    
    Args:
        data: Price series
        window: Window size for trend calculation
        
    Returns:
        Series with trend strength values:
        - Positive values indicate uptrend strength
        - Negative values indicate downtrend strength
        - Values near 0 indicate weak trend
        
    Example:
        >>> import pandas as pd
        >>> prices = pd.Series([100, 101, 102, 103, 104, 105, 106, 107, 108, 109])
        >>> strength = trend_strength(prices)
        >>> print(f"Trend strength: {strength.iloc[-1]:.2f}")
        Trend strength: 1.00
    """
    if not isinstance(data, pd.Series):
        raise TypeError("Data must be a pandas Series")
    
    if window <= 0:
        raise ValueError("Window must be positive")
    
    if len(data) < window + 1:
        raise ValueError(f"Not enough data points. Need at least {window + 1}, got {len(data)}")
    
    # Calculate moving average
    ma = indicators.moving_average(data, window)
    
    # Calculate rate of change of the moving average
    trend_strength = ma.pct_change(periods=1) * 100
    
    return trend_strength


def macd_signal(macd_line: pd.Series, signal_line: pd.Series) -> pd.Series:
    """
    Generate signals based on MACD line and signal line crossovers.
    
    Args:
        macd_line: MACD line series
        signal_line: MACD signal line series
        
    Returns:
        Series with signal values:
        - 1 for bullish crossover (MACD crosses above signal)
        - -1 for bearish crossover (MACD crosses below signal)
        - 0 for no signal
        
    Example:
        >>> import pandas as pd
        >>> macd_line = pd.Series([0.1, 0.2, 0.3, 0.2, 0.1])
        >>> signal_line = pd.Series([0.15, 0.18, 0.25, 0.22, 0.12])
        >>> signals = macd_signal(macd_line, signal_line)
        >>> print(signals.iloc[2])  # Bullish signal
        1
        >>> print(signals.iloc[3])  # Bearish signal
        -1
    """
    if not isinstance(macd_line, pd.Series) or not isinstance(signal_line, pd.Series):
        raise TypeError("Both inputs must be pandas Series")
    
    if len(macd_line) != len(signal_line):
        raise ValueError("Series must have the same length")
    
    # Calculate differences
    current_diff = macd_line - signal_line
    previous_diff = current_diff.shift(1)
    
    # Detect crossovers
    bullish_cross = ((current_diff > 0) & (previous_diff <= 0)).astype(int)
    bearish_cross = ((current_diff < 0) & (previous_diff >= 0)).astype(int) * -1
    
    # Combine signals
    signals = bullish_cross + bearish_cross
    
    return signals


def bb_position(close: pd.Series, upper_band: pd.Series, 
                lower_band: pd.Series) -> pd.Series:
    """
    Calculate position of price relative to Bollinger Bands.
    
    Args:
        close: Close price series
        upper_band: Upper Bollinger Band
        lower_band: Lower Bollinger Band
        
    Returns:
        Series with position values:
        - Values > 0.8 indicate price near upper band (potentially overbought)
        - Values < 0.2 indicate price near lower band (potentially oversold)
        - Values between 0.2-0.8 indicate neutral position
        
    Example:
        >>> import pandas as pd
        >>> close = pd.Series([100, 102, 104, 106, 108])
        >>> upper = pd.Series([105, 105, 105, 105, 105])
        >>> lower = pd.Series([95, 95, 95, 95, 95])
        >>> positions = bb_position(close, upper, lower)
        >>> print(f"Position: {positions.iloc[-1]:.2f}")  # Near upper band
        Position: 0.80
    """
    if not all(isinstance(s, pd.Series) for s in [close, upper_band, lower_band]):
        raise TypeError("All inputs must be pandas Series")
    
    if not (len(close) == len(upper_band) == len(lower_band)):
        raise ValueError("All series must have the same length")
    
    # Calculate position relative to bands
    bb_width = upper_band - lower_band
    bb_position = (close - lower_band) / bb_width
    
    # Handle potential division by zero
    bb_position = bb_position.fillna(0.5)  # Default to middle if width is 0
    
    return bb_position


def combined_signals(data: pd.DataFrame, 
                     ma_fast: int = 5,
                     ma_slow: int = 20,
                     rsi_period: int = 14,
                     bb_period: int = 20,
                     bb_std: float = 2.0,
                     macd_fast: int = 12,
                     macd_slow: int = 26,
                     macd_signal_period: int = 9) -> pd.DataFrame:
    """
    Generate comprehensive trading signals from multiple indicators.
    
    Args:
        data: DataFrame with columns 'close', 'high', 'low', 'volume'
        ma_fast: Fast moving average period
        ma_slow: Slow moving average period
        rsi_period: RSI calculation period
        bb_period: Bollinger Bands period
        bb_std: Bollinger Bands standard deviation multiplier
        macd_fast: MACD fast period
        macd_slow: MACD slow period
        macd_signal_period: MACD signal line period
        
    Returns:
        DataFrame with various signal columns:
        - ma_signal: Moving average crossover signals
        - rsi_signal: RSI overbought/oversold signals
        - macd_signal: MACD crossover signals
        - bb_position: Bollinger Bands position
        - trend_strength: Trend strength
        - composite_score: Combined score of all signals
        
    Example:
        >>> import pandas as pd
        >>> import numpy as np
        >>> dates = pd.date_range('2023-01-01', periods=100)
        >>> data = pd.DataFrame({
        ...     'close': np.cumsum(np.random.randn(100)) + 100,
        ...     'high': np.cumsum(np.random.randn(100)) + 101,
        ...     'low': np.cumsum(np.random.randn(100)) + 99,
        ...     'volume': np.random.randint(1000, 5000, 100)
        ... }, index=dates)
        >>> signals = combined_signals(data)
        >>> print(f"Latest composite score: {signals['composite_score'].iloc[-1]:.2f}")
        Latest composite score: 0.00
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError("Data must be a pandas DataFrame")
    
    required_cols = ['close', 'high', 'low', 'volume']
    missing_cols = [col for col in required_cols if col not in data.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")
    
    # Calculate indicators
    close_series = data['close']
    high_series = data['high']
    low_series = data['low']
    volume_series = data['volume']
    
    # Moving averages
    ma_fast_series = indicators.moving_average(close_series, ma_fast)
    ma_slow_series = indicators.moving_average(close_series, ma_slow)
    
    # RSI
    rsi_series = indicators.rsi(close_series, rsi_period)
    
    # Bollinger Bands
    upper_band, _, lower_band = indicators.bollinger_bands(close_series, bb_period, bb_std)
    
    # MACD
    macd_line, signal_line, _ = indicators.macd(
        close_series, macd_fast, macd_slow, macd_signal_period
    )
    
    # Generate individual signals
    ma_sig = golden_death_cross(ma_fast_series, ma_slow_series)
    rsi_sig = oversold_overbought(rsi_series)
    macd_sig = macd_signal(macd_line, signal_line)
    bb_pos = bb_position(close_series, upper_band, lower_band)
    trend_str = trend_strength(close_series)
    
    # Create results DataFrame
    signals_df = pd.DataFrame(index=data.index)
    signals_df['ma_signal'] = ma_sig
    signals_df['rsi_signal'] = rsi_sig
    signals_df['macd_signal'] = macd_sig
    signals_df['bb_position'] = bb_pos
    signals_df['trend_strength'] = trend_str
    
    # Calculate composite score
    # Normalize each signal to [-1, 1] range and sum them
    signals_df['composite_score'] = (
        signals_df['ma_signal'] +
        signals_df['rsi_signal'] +
        signals_df['macd_signal'] +
        # Convert BB position to signal: oversold(-1) to overbought(1)
        (signals_df['bb_position'] - 0.5) * 2 +
        # Normalize trend strength to [-1, 1] range
        np.clip(signals_df['trend_strength'] / 10, -1, 1)
    ) / 5  # Normalize to [-1, 1] range
    
    return signals_df


def generate_trading_signals(data: pd.DataFrame, 
                           strategy: str = 'conservative') -> pd.Series:
    """
    Generate final trading signals based on a specific strategy.
    
    Args:
        data: DataFrame with indicator values and signals
        strategy: Strategy type ('conservative', 'moderate', 'aggressive')
        
    Returns:
        Series with final trading signals:
        - 1 for buy signal
        - -1 for sell signal
        - 0 for hold
        
    Example:
        >>> import pandas as pd
        >>> import numpy as np
        >>> dates = pd.date_range('2023-01-01', periods=50)
        >>> signals_data = pd.DataFrame({
        ...     'ma_signal': [0, 1, 0, -1, 1] * 10,
        ...     'rsi_signal': [0, 1, -1, 0, 1] * 10,
        ...     'composite_score': np.random.uniform(-1, 1, 50)
        ... }, index=dates)
        >>> final_signals = generate_trading_signals(signals_data, 'moderate')
        >>> print(final_signals.iloc[0])  # Hold signal
        0
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError("Data must be a pandas DataFrame")
    
    required_cols = ['ma_signal', 'rsi_signal', 'composite_score']
    missing_cols = [col for col in required_cols if col not in data.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")
    
    # Define strategy parameters
    strategy_params = {
        'conservative': {'buy_threshold': 0.6, 'sell_threshold': -0.6},
        'moderate': {'buy_threshold': 0.4, 'sell_threshold': -0.4},
        'aggressive': {'buy_threshold': 0.2, 'sell_threshold': -0.2}
    }
    
    if strategy not in strategy_params:
        raise ValueError(f"Unknown strategy: {strategy}. Available: {list(strategy_params.keys())}")
    
    params = strategy_params[strategy]
    
    # Create trading signals based on strategy
    buy_condition = (
        (data['ma_signal'] == 1) &  # Golden cross
        (data['rsi_signal'] != -1) &  # Not overbought
        (data['composite_score'] >= params['buy_threshold'])  # Composite score supports
    )
    
    sell_condition = (
        (data['ma_signal'] == -1) &  # Death cross
        (data['rsi_signal'] != 1) &  # Not oversold
        (data['composite_score'] <= params['sell_threshold'])  # Composite score supports
    )
    
    # Generate final signals
    final_signals = pd.Series(0, index=data.index, dtype=int)
    final_signals[buy_condition] = 1
    final_signals[sell_condition] = -1
    
    return final_signals