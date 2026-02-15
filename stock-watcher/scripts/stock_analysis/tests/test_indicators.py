"""
Unit tests for the indicators module.

This module tests all technical indicators implemented in the stock_analysis.indicators module.
"""

import unittest
import pandas as pd
import numpy as np
from stock_analysis import indicators


class TestIndicators(unittest.TestCase):
    """Test class for technical indicators."""

    def setUp(self):
        """Set up test data for the indicators."""
        # Create sample price data
        self.prices = pd.Series([100, 102, 101, 103, 105, 104, 106, 108, 107, 109], 
                               index=pd.date_range('2023-01-01', periods=10))
        
        # Create sample OHLC data
        self.high = pd.Series([105, 106, 107, 108, 109, 110, 111, 112, 113, 114], 
                             index=pd.date_range('2023-01-01', periods=10))
        self.low = pd.Series([99, 100, 101, 102, 103, 104, 105, 106, 107, 108], 
                            index=pd.date_range('2023-01-01', periods=10))
        self.close = pd.Series([100, 102, 101, 103, 105, 104, 106, 108, 107, 109], 
                              index=pd.date_range('2023-01-01', periods=10))
        self.volume = pd.Series([1000, 1200, 800, 1500, 2000, 1800, 2200, 2500, 1900, 2100], 
                               index=pd.date_range('2023-01-01', periods=10))

    def test_moving_average_basic(self):
        """Test basic functionality of moving average."""
        ma = indicators.moving_average(self.prices, 3)
        self.assertIsInstance(ma, pd.Series)
        self.assertEqual(len(ma), len(self.prices))
        # Check that first 2 values are NaN (not enough data)
        self.assertTrue(pd.isna(ma.iloc[0]))
        self.assertTrue(pd.isna(ma.iloc[1]))
        self.assertFalse(pd.isna(ma.iloc[2]))

    def test_moving_average_invalid_window(self):
        """Test moving average with invalid window."""
        with self.assertRaises(ValueError):
            indicators.moving_average(self.prices, 0)
        
        with self.assertRaises(ValueError):
            indicators.moving_average(self.prices, -5)

    def test_moving_average_insufficient_data(self):
        """Test moving average with insufficient data."""
        short_series = pd.Series([1, 2])
        with self.assertRaises(ValueError):
            indicators.moving_average(short_series, 5)

    def test_ema_basic(self):
        """Test basic functionality of exponential moving average."""
        ema = indicators.ema(self.prices, 3)
        self.assertIsInstance(ema, pd.Series)
        self.assertEqual(len(ema), len(self.prices))

    def test_macd_basic(self):
        """Test basic functionality of MACD."""
        macd_line, signal_line, histogram = indicators.macd(self.prices)
        self.assertIsInstance(macd_line, pd.Series)
        self.assertIsInstance(signal_line, pd.Series)
        self.assertIsInstance(histogram, pd.Series)
        self.assertEqual(len(macd_line), len(self.prices))
        self.assertEqual(len(signal_line), len(self.prices))
        self.assertEqual(len(histogram), len(self.prices))
        # Verify relationship: histogram = macd_line - signal_line
        pd.testing.assert_series_equal(histogram, macd_line - signal_line)

    def test_macd_custom_params(self):
        """Test MACD with custom parameters."""
        macd_line, signal_line, histogram = indicators.macd(self.prices, fast=8, slow=17, signal=6)
        self.assertIsInstance(macd_line, pd.Series)
        self.assertEqual(len(macd_line), len(self.prices))

    def test_macd_invalid_params(self):
        """Test MACD with invalid parameters."""
        with self.assertRaises(ValueError):
            indicators.macd(self.prices, fast=-1, slow=26, signal=9)
        
        with self.assertRaises(ValueError):
            indicators.macd(self.prices, fast=26, slow=12, signal=9)  # fast >= slow

    def test_rsi_basic(self):
        """Test basic functionality of RSI."""
        rsi = indicators.rsi(self.prices)
        self.assertIsInstance(rsi, pd.Series)
        self.assertEqual(len(rsi), len(self.prices))
        # RSI values should be between 0 and 100
        self.assertTrue((rsi >= 0).all() or rsi.isna().all())
        self.assertTrue((rsi <= 100).all() or rsi.isna().all())

    def test_rsi_custom_window(self):
        """Test RSI with custom window."""
        rsi = indicators.rsi(self.prices, window=5)
        self.assertIsInstance(rsi, pd.Series)

    def test_rsi_invalid_window(self):
        """Test RSI with invalid window."""
        with self.assertRaises(ValueError):
            indicators.rsi(self.prices, window=0)
        
        short_series = pd.Series([1, 2])  # Need at least window + 1 points
        with self.assertRaises(ValueError):
            indicators.rsi(short_series, window=5)

    def test_bollinger_bands_basic(self):
        """Test basic functionality of Bollinger Bands."""
        upper, middle, lower = indicators.bollinger_bands(self.prices)
        self.assertIsInstance(upper, pd.Series)
        self.assertIsInstance(middle, pd.Series)
        self.assertIsInstance(lower, pd.Series)
        self.assertEqual(len(upper), len(self.prices))
        self.assertEqual(len(middle), len(self.prices))
        self.assertEqual(len(lower), len(self.prices))
        # Upper band should be >= middle >= lower (except for NaN values)
        valid_indices = ~(upper.isna() | middle.isna() | lower.isna())
        self.assertTrue((upper[valid_indices] >= middle[valid_indices]).all())
        self.assertTrue((middle[valid_indices] >= lower[valid_indices]).all())

    def test_bollinger_bands_custom_params(self):
        """Test Bollinger Bands with custom parameters."""
        upper, middle, lower = indicators.bollinger_bands(self.prices, window=10, num_std=1.5)
        self.assertIsInstance(upper, pd.Series)

    def test_bollinger_bands_invalid_params(self):
        """Test Bollinger Bands with invalid parameters."""
        with self.assertRaises(ValueError):
            indicators.bollinger_bands(self.prices, window=0, num_std=2.0)
        
        with self.assertRaises(ValueError):
            indicators.bollinger_bands(self.prices, window=10, num_std=0)

    def test_kdj_basic(self):
        """Test basic functionality of KDJ indicator."""
        k, d, j = indicators.kdj(self.high, self.low, self.close)
        self.assertIsInstance(k, pd.Series)
        self.assertIsInstance(d, pd.Series)
        self.assertIsInstance(j, pd.Series)
        self.assertEqual(len(k), len(self.high))
        self.assertEqual(len(d), len(self.high))
        self.assertEqual(len(j), len(self.high))

    def test_kdj_invalid_inputs(self):
        """Test KDJ with invalid inputs."""
        # Different lengths
        with self.assertRaises(ValueError):
            indicators.kdj(self.high[:-1], self.low, self.close)
        
        # Invalid windows
        with self.assertRaises(ValueError):
            indicators.kdj(self.high, self.low, self.close, k_window=0)

    def test_obv_basic(self):
        """Test basic functionality of OBV."""
        obv = indicators.obv(self.close, self.volume)
        self.assertIsInstance(obv, pd.Series)
        self.assertEqual(len(obv), len(self.close))
        # OBV should be cumulative
        self.assertTrue((obv.diff().dropna() >= -self.volume).all() or obv.isna().all())

    def test_obv_invalid_inputs(self):
        """Test OBV with invalid inputs."""
        # Different lengths
        with self.assertRaises(ValueError):
            indicators.obv(self.close[:-1], self.volume)
        
        # Insufficient data
        short_close = pd.Series([100])
        short_volume = pd.Series([1000])
        with self.assertRaises(ValueError):
            indicators.obv(short_close, short_volume)

    def test_volume_ma_basic(self):
        """Test basic functionality of volume moving average."""
        vol_ma = indicators.volume_ma(self.volume, 3)
        self.assertIsInstance(vol_ma, pd.Series)
        self.assertEqual(len(vol_ma), len(self.volume))

    def test_ma_system_basic(self):
        """Test basic functionality of MA system."""
        mas = indicators.ma_system(self.prices)
        self.assertIsInstance(mas, dict)
        expected_keys = ['MA5', 'MA10', 'MA20', 'MA60']
        for key in expected_keys:
            self.assertIn(key, mas)
            self.assertIsInstance(mas[key], pd.Series)

    def test_ma_system_insufficient_data(self):
        """Test MA system with insufficient data."""
        short_series = pd.Series(range(10))  # Less than 60 needed for full system
        with self.assertRaises(ValueError):
            indicators.ma_system(short_series)

    def test_validate_input_basic(self):
        """Test basic functionality of input validation."""
        validated = indicators.validate_input(self.prices)
        self.assertIsInstance(validated, pd.Series)
        # Should remove NaN values
        series_with_nan = self.prices.copy()
        series_with_nan.iloc[0] = np.nan
        validated_with_nan = indicators.validate_input(series_with_nan)
        self.assertEqual(len(validated_with_nan), len(self.prices) - 1)

    def test_validate_input_invalid_type(self):
        """Test input validation with invalid type."""
        with self.assertRaises(TypeError):
            indicators.validate_input([1, 2, 3])  # Not a pandas Series

    def test_validate_input_empty(self):
        """Test input validation with empty series."""
        empty_series = pd.Series([], dtype=float)
        with self.assertRaises(ValueError):
            indicators.validate_input(empty_series)

    def test_edge_cases(self):
        """Test edge cases for indicators."""
        # Single value
        single_val = pd.Series([100])
        with self.assertRaises(ValueError):
            indicators.moving_average(single_val, 5)
        
        # All same values
        same_vals = pd.Series([100] * 10)
        ma = indicators.moving_average(same_vals, 3)
        # After the initial NaN values, all MA values should be 100
        self.assertTrue((ma.dropna() == 100).all())
        
        # Series with NaN in middle
        series_with_nan = self.prices.copy()
        series_with_nan.iloc[5] = np.nan
        ma = indicators.moving_average(series_with_nan, 3)
        self.assertTrue(pd.isna(ma.iloc[5]))  # Should be NaN where input was NaN


class TestIndicatorsWithRealisticData(unittest.TestCase):
    """Test indicators with more realistic financial data."""

    def setUp(self):
        """Set up more realistic test data."""
        np.random.seed(42)  # For reproducible results
        # Simulate realistic price data (random walk)
        returns = np.random.normal(0.001, 0.02, 100)  # Daily returns: mean 0.1%, std 2%
        prices = [100]  # Starting price
        for ret in returns[1:]:
            prices.append(prices[-1] * (1 + ret))
        
        self.realistic_prices = pd.Series(prices, 
                                         index=pd.date_range('2023-01-01', periods=len(prices)))
        self.realistic_volume = pd.Series(np.random.randint(1000, 5000, len(prices)), 
                                         index=pd.date_range('2023-01-01', periods=len(prices)))

    def test_indicators_with_realistic_data(self):
        """Test that indicators work with realistic data."""
        # Test all major indicators with realistic data
        ma = indicators.moving_average(self.realistic_prices, 20)
        self.assertIsInstance(ma, pd.Series)
        self.assertEqual(len(ma), len(self.realistic_prices))
        
        ema = indicators.ema(self.realistic_prices, 10)
        self.assertIsInstance(ema, pd.Series)
        
        macd_line, signal_line, hist = indicators.macd(self.realistic_prices)
        self.assertIsInstance(macd_line, pd.Series)
        
        rsi = indicators.rsi(self.realistic_prices)
        self.assertIsInstance(rsi, pd.Series)
        
        upper, middle, lower = indicators.bollinger_bands(self.realistic_prices)
        self.assertIsInstance(upper, pd.Series)
        
        vol_ma = indicators.volume_ma(self.realistic_volume, 20)
        self.assertIsInstance(vol_ma, pd.Series)


if __name__ == '__main__':
    unittest.main()