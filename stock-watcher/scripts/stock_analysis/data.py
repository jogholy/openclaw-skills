"""
Data Processing Module

This module provides functions for cleaning, validating, and transforming financial data.

Functions:
    - validate_ohlcv: Validate OHLCV data format
    - clean_missing_values: Handle missing values in financial data
    - resample_data: Resample data to different timeframes
    - detect_outliers: Detect outliers in financial data
    - calculate_returns: Calculate price returns
"""

import numpy as np
import pandas as pd
from typing import Union, Dict, List, Optional, Tuple
from datetime import datetime


def validate_ohlcv(data: pd.DataFrame) -> bool:
    """
    Validate that the DataFrame has proper OHLCV format.
    
    Args:
        data: DataFrame with financial data
        
    Returns:
        True if valid, raises ValueError otherwise
        
    Example:
        >>> df = pd.DataFrame({
        ...     'open': [100, 101, 102],
        ...     'high': [102, 103, 104],
        ...     'low': [99, 100, 101],
        ...     'close': [101, 102, 103],
        ...     'volume': [1000, 1200, 800]
        ... }, index=pd.date_range('2023-01-01', periods=3))
        >>> is_valid = validate_ohlcv(df)
        >>> print(is_valid)
        True
    """
    required_columns = ['open', 'high', 'low', 'close', 'volume']
    
    # Check if all required columns exist
    missing_cols = [col for col in required_columns if col not in data.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")
    
    # Check if index is datetime
    if not isinstance(data.index, pd.DatetimeIndex):
        raise ValueError("DataFrame index must be a DatetimeIndex")
    
    # Check for non-numeric data
    numeric_cols = ['open', 'high', 'low', 'close']
    for col in numeric_cols:
        if not pd.api.types.is_numeric_dtype(data[col]):
            raise ValueError(f"Column '{col}' must contain numeric data")
    
    # Check for negative volumes
    if (data['volume'] < 0).any():
        raise ValueError("Volume cannot be negative")
    
    # Check OHLC relationships
    invalid_relationships = (
        (data['high'] < data['low']) |
        (data['high'] < data['close']) |
        (data['high'] < data['open']) |
        (data['low'] > data['close']) |
        (data['low'] > data['open'])
    )
    
    if invalid_relationships.any():
        invalid_dates = data[invalid_relationships].index.tolist()
        raise ValueError(f"Invalid OHLC relationships found at dates: {invalid_dates[:5]}...")
    
    return True


def clean_missing_values(data: pd.DataFrame, 
                        method: str = 'forward_fill',
                        threshold: float = 0.1) -> pd.DataFrame:
    """
    Clean missing values in financial data.
    
    Args:
        data: DataFrame with financial data
        method: Method to handle missing values ('forward_fill', 'backward_fill', 'interpolate', 'drop')
        threshold: Maximum fraction of missing values allowed per column
        
    Returns:
        Cleaned DataFrame
        
    Example:
        >>> df = pd.DataFrame({
        ...     'close': [100, np.nan, 102, 103, np.nan, 105],
        ...     'volume': [1000, 1100, np.nan, 1300, 1400, 1500]
        ... }, index=pd.date_range('2023-01-01', periods=6))
        >>> cleaned_df = clean_missing_values(df, method='interpolate')
        >>> print(cleaned_df.isnull().sum().sum())  # Should be 0
        0
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError("Data must be a pandas DataFrame")
    
    # Check missing value threshold
    missing_pct = data.isnull().sum() / len(data)
    exceeding_cols = missing_pct[missing_pct > threshold].index.tolist()
    
    if exceeding_cols:
        raise ValueError(f"Columns exceed missing value threshold ({threshold*100}%): {exceeding_cols}")
    
    if method == 'forward_fill':
        cleaned_data = data.fillna(method='ffill').fillna(method='bfill')
    elif method == 'backward_fill':
        cleaned_data = data.fillna(method='bfill').fillna(method='ffill')
    elif method == 'interpolate':
        cleaned_data = data.interpolate(method='linear').fillna(method='ffill').fillna(method='bfill')
    elif method == 'drop':
        cleaned_data = data.dropna()
    else:
        raise ValueError(f"Unknown method: {method}. Use 'forward_fill', 'backward_fill', 'interpolate', or 'drop'")
    
    return cleaned_data


def resample_data(data: pd.DataFrame, 
                 timeframe: str = '1D',
                 agg_dict: Optional[Dict[str, Union[str, List]]] = None) -> pd.DataFrame:
    """
    Resample financial data to a different timeframe.
    
    Args:
        data: DataFrame with OHLCV data
        timeframe: Target timeframe ('1D', '1W', '1M', '3M', etc.)
        agg_dict: Dictionary specifying aggregation methods for each column
        
    Returns:
        Resampled DataFrame
        
    Example:
        >>> df = pd.DataFrame({
        ...     'open': [100, 101, 102, 103, 104],
        ...     'high': [102, 103, 104, 105, 106],
        ...     'low': [99, 100, 101, 102, 103],
        ...     'close': [101, 102, 103, 104, 105],
        ...     'volume': [1000, 1100, 1200, 1300, 1400]
        ... }, index=pd.date_range('2023-01-01', periods=5, freq='H'))
        >>> weekly_data = resample_data(df, '1D')
        >>> print(len(weekly_data))  # Should be 5 (daily data)
        5
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError("Data must be a pandas DataFrame")
    
    if agg_dict is None:
        # Default aggregation dictionary for OHLCV data
        agg_dict = {
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }
    
    try:
        resampled = data.resample(timeframe).agg(agg_dict)
        return resampled
    except Exception as e:
        raise ValueError(f"Error resampling data: {str(e)}")


def detect_outliers(data: pd.Series, 
                   method: str = 'iqr',
                   threshold: float = 2.0) -> pd.Series:
    """
    Detect outliers in a financial series.
    
    Args:
        data: Series with financial data
        method: Method for outlier detection ('iqr', 'zscore', 'modified_zscore')
        threshold: Threshold for outlier detection
        
    Returns:
        Boolean Series indicating outliers
        
    Example:
        >>> prices = pd.Series([100, 101, 102, 103, 150, 104, 105])  # 150 is outlier
        >>> outliers = detect_outliers(prices, method='iqr')
        >>> print(outliers.iloc[4])  # Should be True for the outlier
        True
    """
    if not isinstance(data, pd.Series):
        raise TypeError("Data must be a pandas Series")
    
    if method == 'iqr':
        Q1 = data.quantile(0.25)
        Q3 = data.quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - threshold * IQR
        upper_bound = Q3 + threshold * IQR
        outliers = (data < lower_bound) | (data > upper_bound)
    elif method == 'zscore':
        z_scores = np.abs((data - data.mean()) / data.std())
        outliers = z_scores > threshold
    elif method == 'modified_zscore':
        median = data.median()
        mad = np.median(np.abs(data - median))  # Median Absolute Deviation
        modified_z_scores = 0.6745 * (data - median) / mad
        outliers = np.abs(modified_z_scores) > threshold
    else:
        raise ValueError(f"Unknown method: {method}. Use 'iqr', 'zscore', or 'modified_zscore'")
    
    return outliers


def remove_outliers(data: pd.DataFrame, 
                   columns: Optional[List[str]] = None,
                   method: str = 'iqr',
                   threshold: float = 2.0) -> pd.DataFrame:
    """
    Remove outliers from financial data.
    
    Args:
        data: DataFrame with financial data
        columns: List of columns to check for outliers (default: all numeric columns)
        method: Method for outlier detection
        threshold: Threshold for outlier detection
        
    Returns:
        DataFrame with outliers removed
        
    Example:
        >>> df = pd.DataFrame({
        ...     'close': [100, 101, 102, 103, 150, 104, 105],  # 150 is outlier
        ...     'volume': [1000, 1100, 1200, 1300, 5000, 1400, 1500]  # 5000 is outlier
        ... }, index=pd.date_range('2023-01-01', periods=7))
        >>> clean_df = remove_outliers(df)
        >>> print(len(clean_df))  # Should be 6 (one row removed)
        6
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError("Data must be a pandas DataFrame")
    
    if columns is None:
        # Select all numeric columns
        columns = data.select_dtypes(include=[np.number]).columns.tolist()
    
    # Start with all rows included
    mask = pd.Series([True] * len(data), index=data.index)
    
    for col in columns:
        if col in data.columns:
            col_outliers = detect_outliers(data[col], method=method, threshold=threshold)
            # Exclude rows where any specified column has an outlier
            mask = mask & ~col_outliers
    
    return data[mask]


def calculate_returns(data: pd.Series, 
                     method: str = 'log',
                     periods: int = 1) -> pd.Series:
    """
    Calculate returns from price data.
    
    Args:
        data: Series with price data
        method: Method for calculating returns ('simple' or 'log')
        periods: Number of periods for return calculation
        
    Returns:
        Series with return values
        
    Example:
        >>> prices = pd.Series([100, 105, 102, 108, 110])
        >>> returns = calculate_returns(prices, method='simple')
        >>> print(f"First return: {returns.iloc[1]:.4f}")
        First return: 0.0500
    """
    if not isinstance(data, pd.Series):
        raise TypeError("Data must be a pandas Series")
    
    if method == 'simple':
        returns = data.pct_change(periods=periods)
    elif method == 'log':
        returns = np.log(data / data.shift(periods=periods))
    else:
        raise ValueError(f"Unknown method: {method}. Use 'simple' or 'log'")
    
    return returns


def calculate_cumulative_returns(returns: pd.Series) -> pd.Series:
    """
    Calculate cumulative returns from period returns.
    
    Args:
        returns: Series with period returns
        
    Returns:
        Series with cumulative returns
        
    Example:
        >>> returns = pd.Series([0.05, -0.02, 0.03, 0.01])
        >>> cum_returns = calculate_cumulative_returns(returns)
        >>> print(f"Cumulative return: {cum_returns.iloc[-1]:.4f}")
        Cumulative return: 0.0703
    """
    if not isinstance(returns, pd.Series):
        raise TypeError("Returns must be a pandas Series")
    
    # Calculate cumulative returns: (1 + r1) * (1 + r2) * ... - 1
    cumulative_returns = (1 + returns.fillna(0)).cumprod() - 1
    return cumulative_returns


def align_dataframes(df1: pd.DataFrame, 
                    df2: pd.DataFrame, 
                    join_type: str = 'inner') -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Align two DataFrames by their datetime index.
    
    Args:
        df1: First DataFrame
        df2: Second DataFrame
        join_type: Type of join ('inner', 'outer', 'left', 'right')
        
    Returns:
        Tuple of aligned DataFrames
        
    Example:
        >>> df1 = pd.DataFrame({'close': [100, 101, 102]}, 
        ...                   index=pd.date_range('2023-01-01', periods=3))
        >>> df2 = pd.DataFrame({'volume': [1000, 1100, 1200, 1300]}, 
        ...                   index=pd.date_range('2023-01-01', periods=4))
        >>> aligned_df1, aligned_df2 = align_dataframes(df1, df2)
        >>> print(len(aligned_df1))  # Should match the shorter series
        3
    """
    if not isinstance(df1, pd.DataFrame) or not isinstance(df2, pd.DataFrame):
        raise TypeError("Both inputs must be pandas DataFrames")
    
    if not isinstance(df1.index, pd.DatetimeIndex) or not isinstance(df2.index, pd.DatetimeIndex):
        raise ValueError("Both DataFrames must have DatetimeIndex")
    
    # Perform the join
    if join_type == 'inner':
        common_index = df1.index.intersection(df2.index)
        aligned_df1 = df1.loc[common_index]
        aligned_df2 = df2.loc[common_index]
    elif join_type == 'outer':
        common_index = df1.index.union(df2.index)
        aligned_df1 = df1.reindex(common_index)
        aligned_df2 = df2.reindex(common_index)
    elif join_type == 'left':
        aligned_df1 = df1
        aligned_df2 = df2.reindex(df1.index)
    elif join_type == 'right':
        aligned_df1 = df1.reindex(df2.index)
        aligned_df2 = df2
    else:
        raise ValueError(f"Unknown join type: {join_type}. Use 'inner', 'outer', 'left', or 'right'")
    
    return aligned_df1, aligned_df2


def normalize_data(data: pd.DataFrame, 
                  method: str = 'min_max',
                  columns: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Normalize financial data.
    
    Args:
        data: DataFrame with financial data
        method: Normalization method ('min_max', 'z_score', 'robust')
        columns: List of columns to normalize (default: all numeric columns)
        
    Returns:
        Normalized DataFrame
        
    Example:
        >>> df = pd.DataFrame({
        ...     'close': [100, 105, 110, 115, 120],
        ...     'volume': [1000, 1100, 1200, 1300, 1400]
        ... })
        >>> normalized_df = normalize_data(df, method='min_max')
        >>> print(f"Normalized close range: [{normalized_df['close'].min():.3f}, {normalized_df['close'].max():.3f}]")
        Normalized close range: [0.000, 1.000]
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError("Data must be a pandas DataFrame")
    
    if columns is None:
        columns = data.select_dtypes(include=[np.number]).columns.tolist()
    
    normalized_data = data.copy()
    
    for col in columns:
        if col in data.columns:
            if method == 'min_max':
                min_val = data[col].min()
                max_val = data[col].max()
                if max_val != min_val:  # Avoid division by zero
                    normalized_data[col] = (data[col] - min_val) / (max_val - min_val)
                else:
                    normalized_data[col] = 0.0
            elif method == 'z_score':
                mean_val = data[col].mean()
                std_val = data[col].std()
                if std_val != 0:  # Avoid division by zero
                    normalized_data[col] = (data[col] - mean_val) / std_val
                else:
                    normalized_data[col] = 0.0
            elif method == 'robust':
                median_val = data[col].median()
                mad = np.median(np.abs(data[col] - median_val))  # Median Absolute Deviation
                if mad != 0:  # Avoid division by zero
                    normalized_data[col] = (data[col] - median_val) / mad
                else:
                    normalized_data[col] = 0.0
            else:
                raise ValueError(f"Unknown normalization method: {method}")
    
    return normalized_data


def prepare_features(data: pd.DataFrame, 
                    feature_columns: List[str],
                    target_column: str,
                    lookback_period: int = 1) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Prepare features and target for machine learning models.
    
    Args:
        data: DataFrame with financial data
        feature_columns: List of columns to use as features
        target_column: Column to predict
        lookback_period: Number of periods to shift target
        
    Returns:
        Tuple of (features DataFrame, target Series)
        
    Example:
        >>> df = pd.DataFrame({
        ...     'close': [100, 101, 102, 103, 104, 105],
        ...     'volume': [1000, 1100, 1200, 1300, 1400, 1500],
        ...     'rsi': [30, 40, 50, 60, 70, 80]
        ... })
        >>> features, target = prepare_features(df, ['rsi', 'volume'], 'close', lookback_period=1)
        >>> print(f"Features shape: {features.shape}")
        Features shape: (5, 2)
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError("Data must be a pandas DataFrame")
    
    missing_cols = [col for col in feature_columns + [target_column] if col not in data.columns]
    if missing_cols:
        raise ValueError(f"Missing columns: {missing_cols}")
    
    # Create features DataFrame
    features = data[feature_columns].copy()
    
    # Create target Series shifted by lookback_period
    target = data[target_column].shift(-lookback_period)
    
    # Align features and target (remove rows with NaN values)
    combined = pd.concat([features, target], axis=1).dropna()
    
    # Separate back into features and target
    aligned_features = combined[feature_columns]
    aligned_target = combined[target_column]
    
    return aligned_features, aligned_target


def split_time_series(data: pd.DataFrame, 
                     train_ratio: float = 0.7,
                     val_ratio: float = 0.15) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Split time series data chronologically into train, validation, and test sets.
    
    Args:
        data: DataFrame with time series data
        train_ratio: Proportion of data for training
        val_ratio: Proportion of data for validation (test gets the remainder)
        
    Returns:
        Tuple of (train_df, val_df, test_df)
        
    Example:
        >>> df = pd.DataFrame({'close': range(100)}, 
        ...                  index=pd.date_range('2023-01-01', periods=100))
        >>> train, val, test = split_time_series(df, train_ratio=0.6, val_ratio=0.2)
        >>> print(f"Train: {len(train)}, Val: {len(val)}, Test: {len(test)}")
        Train: 60, Val: 20, Test: 20
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError("Data must be a pandas DataFrame")
    
    if not (0 < train_ratio < 1) or not (0 < val_ratio < 1) or (train_ratio + val_ratio >= 1):
        raise ValueError("Ratios must be between 0 and 1, and train_ratio + val_ratio must be less than 1")
    
    n = len(data)
    train_end = int(n * train_ratio)
    val_end = int(n * (train_ratio + val_ratio))
    
    train_data = data.iloc[:train_end]
    val_data = data.iloc[train_end:val_end]
    test_data = data.iloc[val_end:]
    
    return train_data, val_data, test_data