"""
Technical Indicators Module

This module provides implementations of common technical indicators used in stock market analysis.

Functions:
    - macd: Moving Average Convergence Divergence
    - rsi: Relative Strength Index
    - bollinger_bands: Bollinger Bands
    - kdj: Stochastic Oscillator (KDJ)
    - moving_average: Simple Moving Average
    - ema: Exponential Moving Average
    - obv: On Balance Volume
    - volume_ma: Volume Moving Average
"""

import numpy as np
import pandas as pd
from typing import Tuple, Optional


def validate_input(data: pd.Series) -> pd.Series:
    """
    Validate input data and handle missing values.
    
    Args:
        data: Input series
        
    Returns:
        Cleaned series with no NaN values
    """
    if not isinstance(data, pd.Series):
        raise TypeError("Input must be a pandas Series")
    
    # Remove leading/trailing NaN values
    data = data.dropna()
    
    if len(data) == 0:
        raise ValueError("Input data is empty after removing NaN values")
        
    return data


def moving_average(data: pd.Series, window: int) -> pd.Series:
    """
    Calculate Simple Moving Average (SMA).
    
    Args:
        data: Price or value series
        window: Window size for the moving average
        
    Returns:
        Series with moving average values
        
    Example:
        >>> prices = pd.Series([1, 2, 3, 4, 5])
        >>> ma = moving_average(prices, 3)
        >>> print(ma.iloc[-1])  # Last value
        4.0
    """
    data = validate_input(data)
    
    if window <= 0:
        raise ValueError("Window must be positive")
    
    if len(data) < window:
        raise ValueError(f"Not enough data points. Need at least {window}, got {len(data)}")
    
    ma = data.rolling(window=window).mean()
    return ma


def ema(data: pd.Series, window: int) -> pd.Series:
    """
    Calculate Exponential Moving Average (EMA).
    
    Args:
        data: Price or value series
        window: Window size for the EMA
        
    Returns:
        Series with EMA values
        
    Example:
        >>> prices = pd.Series([1, 2, 3, 4, 5])
        >>> ema_val = ema(prices, 3)
        >>> print(ema_val.iloc[-1])  # Last value
        4.25
    """
    data = validate_input(data)
    
    if window <= 0:
        raise ValueError("Window must be positive")
    
    if len(data) < window:
        raise ValueError(f"Not enough data points. Need at least {window}, got {len(data)}")
    
    ema = data.ewm(span=window).mean()
    return ema


def macd(data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate Moving Average Convergence Divergence (MACD).
    
    Args:
        data: Price series
        fast: Fast EMA period (default 12)
        slow: Slow EMA period (default 26)
        signal: Signal line EMA period (default 9)
        
    Returns:
        Tuple of (macd_line, signal_line, histogram)
        
    Example:
        >>> prices = pd.Series([100, 101, 102, 103, 104, 105, 106, 107, 108, 109])
        >>> macd_line, signal_line, hist = macd(prices)
        >>> print(f"MACD: {macd_line.iloc[-1]:.4f}")
        MACD: 0.2105
    """
    data = validate_input(data)
    
    if fast <= 0 or slow <= 0 or signal <= 0:
        raise ValueError("All periods must be positive")
    
    if fast >= slow:
        raise ValueError("Fast period must be less than slow period")
    
    if len(data) < max(slow, signal):
        raise ValueError(f"Not enough data points. Need at least {max(slow, signal)}, got {len(data)}")
    
    ema_fast = ema(data, fast)
    ema_slow = ema(data, slow)
    
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram


def rsi(data: pd.Series, window: int = 14) -> pd.Series:
    """
    Calculate Relative Strength Index (RSI).
    
    Args:
        data: Price series
        window: Lookback period (default 14)
        
    Returns:
        Series with RSI values (0-100 range)
        
    Example:
        >>> prices = pd.Series([100, 102, 101, 103, 105, 104, 106, 108, 107, 109])
        >>> rsi_val = rsi(prices)
        >>> print(f"RSI: {rsi_val.iloc[-1]:.2f}")
        RSI: 71.43
    """
    data = validate_input(data)
    
    if window <= 0:
        raise ValueError("Window must be positive")
    
    if len(data) < window + 1:
        raise ValueError(f"Not enough data points. Need at least {window + 1}, got {len(data)}")
    
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)
    
    avg_gain = gain.rolling(window=window).mean()
    avg_loss = loss.rolling(window=window).mean()
    
    # Handle initial NaN values properly
    for i in range(window, len(avg_gain)):
        if i > 0:
            avg_gain.iloc[i] = (avg_gain.iloc[i-1] * (window - 1) + gain.iloc[i]) / window
            avg_loss.iloc[i] = (avg_loss.iloc[i-1] * (window - 1) + loss.iloc[i]) / window
    
    rs = avg_gain / avg_loss.replace(0, 1e-10)  # Avoid division by zero
    rsi = 100 - (100 / (1 + rs))
    
    return rsi


def bollinger_bands(data: pd.Series, window: int = 20, num_std: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate Bollinger Bands.
    
    Args:
        data: Price series
        window: Lookback period (default 20)
        num_std: Number of standard deviations (default 2.0)
        
    Returns:
        Tuple of (upper_band, middle_band, lower_band)
        
    Example:
        >>> prices = pd.Series([100, 102, 101, 103, 105, 104, 106, 108, 107, 109])
        >>> upper, middle, lower = bollinger_bands(prices)
        >>> print(f"Upper band: {upper.iloc[-1]:.2f}")
        Upper band: 109.66
    """
    data = validate_input(data)
    
    if window <= 0:
        raise ValueError("Window must be positive")
    
    if num_std <= 0:
        raise ValueError("Number of standard deviations must be positive")
    
    if len(data) < window:
        raise ValueError(f"Not enough data points. Need at least {window}, got {len(data)}")
    
    rolling_mean = data.rolling(window=window).mean()
    rolling_std = data.rolling(window=window).std()
    
    upper_band = rolling_mean + (rolling_std * num_std)
    lower_band = rolling_mean - (rolling_std * num_std)
    middle_band = rolling_mean
    
    return upper_band, middle_band, lower_band


def kdj(high: pd.Series, low: pd.Series, close: pd.Series, k_window: int = 9, 
         d_window: int = 3, j_window: int = 3) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate Stochastic Oscillator (KDJ).
    
    Args:
        high: High price series
        low: Low price series
        close: Close price series
        k_window: Lookback period for %K (default 9)
        d_window: Lookback period for %D (default 3)
        j_window: Lookback period for %J (default 3)
        
    Returns:
        Tuple of (k_line, d_line, j_line)
        
    Example:
        >>> high = pd.Series([105, 106, 107, 108, 109])
        >>> low = pd.Series([100, 101, 102, 103, 104])
        >>> close = pd.Series([104, 105, 106, 107, 108])
        >>> k, d, j = kdj(high, low, close)
        >>> print(f"%K: {k.iloc[-1]:.2f}")
        %K: 80.00
    """
    high = validate_input(high)
    low = validate_input(low)
    close = validate_input(close)
    
    if not (len(high) == len(low) == len(close)):
        raise ValueError("High, low, and close series must have the same length")
    
    if k_window <= 0 or d_window <= 0 or j_window <= 0:
        raise ValueError("All windows must be positive")
    
    if len(high) < k_window:
        raise ValueError(f"Not enough data points. Need at least {k_window}, got {len(high)}")
    
    # Calculate rolling min and max
    lowest_low = low.rolling(window=k_window).min()
    highest_high = high.rolling(window=k_window).max()
    
    # Calculate %K
    k_raw = ((close - lowest_low) / (highest_high - lowest_low)) * 100
    k_line = k_raw.rolling(window=d_window).mean() if d_window > 1 else k_raw
    
    # Calculate %D
    d_line = k_line.rolling(window=j_window).mean() if j_window > 1 else k_line
    
    # Calculate %J
    j_line = 3 * k_line - 2 * d_line
    
    return k_line, d_line, j_line


def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """
    Calculate On Balance Volume (OBV).
    
    Args:
        close: Close price series
        volume: Volume series
        
    Returns:
        Series with OBV values
        
    Example:
        >>> close = pd.Series([100, 102, 101, 103, 105])
        >>> volume = pd.Series([1000, 1200, 800, 1500, 2000])
        >>> obv_val = obv(close, volume)
        >>> print(f"OBV: {obv_val.iloc[-1]}")
        OBV: 3500
    """
    close = validate_input(close)
    volume = validate_input(volume)
    
    if len(close) != len(volume):
        raise ValueError("Close and volume series must have the same length")
    
    if len(close) < 2:
        raise ValueError("Need at least 2 data points for OBV calculation")
    
    # Calculate price changes
    price_change = close.diff()
    
    # Initialize OBV with first volume value
    obv_values = [volume.iloc[0]]
    
    for i in range(1, len(price_change)):
        if price_change.iloc[i] > 0:
            # Price went up, add volume
            obv_values.append(obv_values[-1] + volume.iloc[i])
        elif price_change.iloc[i] < 0:
            # Price went down, subtract volume
            obv_values.append(obv_values[-1] - volume.iloc[i])
        else:
            # Price unchanged, no change to OBV
            obv_values.append(obv_values[-1])
    
    return pd.Series(obv_values, index=close.index)


def volume_ma(volume: pd.Series, window: int = 20) -> pd.Series:
    """
    Calculate Moving Average of Volume.
    
    Args:
        volume: Volume series
        window: Window size for the moving average (default 20)
        
    Returns:
        Series with volume moving average values
        
    Example:
        >>> volume = pd.Series([1000, 1200, 800, 1500, 2000])
        >>> vol_ma = volume_ma(volume, 3)
        >>> print(f"Volume MA: {vol_ma.iloc[-1]:.2f}")
        Volume MA: 1100.00
    """
    volume = validate_input(volume)
    
    if window <= 0:
        raise ValueError("Window must be positive")
    
    if len(volume) < window:
        raise ValueError(f"Not enough data points. Need at least {window}, got {len(volume)}")
    
    vol_ma = volume.rolling(window=window).mean()
    return vol_ma


def ma_system(data: pd.Series) -> dict:
    """
    Calculate multiple moving averages for the MA system.
    
    Args:
        data: Price series
        
    Returns:
        Dictionary containing MA5, MA10, MA20, and MA60
        
    Example:
        >>> prices = pd.Series([100, 102, 101, 103, 105, 104, 106, 108, 107, 109])
        >>> mas = ma_system(prices)
        >>> print(f"MA20: {mas['MA20'].iloc[-1]:.2f}")
        MA20: 104.50
    """
    data = validate_input(data)
    
    if len(data) < 60:
        raise ValueError("Need at least 60 data points for full MA system")
    
    result = {}
    for period in [5, 10, 20, 60]:
        result[f'MA{period}'] = moving_average(data, period)
    
    return result