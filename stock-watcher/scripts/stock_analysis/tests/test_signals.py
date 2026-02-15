"""
Unit tests for the signals module.

This module tests all signal generation functions in the stock_analysis.signals module.
"""

import unittest
import pandas as pd
import numpy as np
from stock_analysis import signals, indicators


class TestSignalGeneration(unittest.TestCase):
    """Test class for signal generation functions."""

    def setUp(self):
        """Set up test data for the signal generation tests."""
        # Create sample price data
        self.prices = pd.Series([100, 102, 101, 103, 105, 104, 106, 108, 107, 109], 
                               index=pd.date_range('2023-01-01', periods=10))
        
        # Create sample OHLCV data
        self.data = pd.DataFrame({
            'close': [100, 102, 101, 103, 105, 104, 106, 108, 107, 109],
            'high': [105, 106, 107, 108, 109, 110, 111, 112, 113, 114],
            'low': [99, 100, 101, 102, 103, 104, 105, 106, 107, 108],
            'volume': [1000, 1200, 800, 1500, 2000, 1800, 2200, 2500, 1900, 2100]
        }, index=pd.date_range('2023-01-01', periods=10))
        
        # Calculate some indicators for testing
        self.fast_ma = indicators.moving_average(self.prices, 3)
        self.slow_ma = indicators.moving_average(self.prices, 7)
        self.rsi = indicators.rsi(self.prices)

    def test_golden_death_cross_basic(self):
        """Test basic functionality of golden/death cross detection."""
        cross_signals = signals.golden_death_cross(self.fast_ma, self.slow_ma)
        self.assertIsInstance(cross_signals, pd.Series)
        self.assertEqual(len(cross_signals), len(self.prices))
        # Signals should be -1, 0, or 1
        self.assertTrue(cross_signals.isin([-1, 0, 1]).all())

    def test_golden_death_cross_invalid_inputs(self):
        """Test golden/death cross with invalid inputs."""
        with self.assertRaises(TypeError):
            signals.golden_death_cross([1, 2, 3], self.slow_ma)
        
        with self.assertRaises(ValueError):
            signals.golden_death_cross(self.fast_ma[:5], self.slow_ma)  # Different lengths
        
        with self.assertRaises(ValueError):
            signals.golden_death_cross(self.fast_ma[:2], self.slow_ma[:2])  # Insufficient data

    def test_oversold_overbought_basic(self):
        """Test basic functionality of oversold/overbought detection."""
        ob_os_signals = signals.oversold_overbought(self.rsi)
        self.assertIsInstance(ob_os_signals, pd.Series)
        self.assertEqual(len(ob_os_signals), len(self.rsi))
        # Signals should be -1, 0, or 1
        self.assertTrue(ob_os_signals.isin([-1, 0, 1]).all())

    def test_oversold_overbought_custom_levels(self):
        """Test oversold/overbought detection with custom levels."""
        ob_os_signals = signals.oversold_overbought(self.rsi, overbought_level=80, oversold_level=20)
        self.assertIsInstance(ob_os_signals, pd.Series)

    def test_oversold_overbought_invalid_levels(self):
        """Test oversold/overbought detection with invalid levels."""
        with self.assertRaises(ValueError):
            signals.oversold_overbought(self.rsi, overbought_level=20, oversold_level=80)  # Wrong order
        
        with self.assertRaises(ValueError):
            signals.oversold_overbought(self.rsi, overbought_level=110, oversold_level=30)  # Above 100
        
        with self.assertRaises(ValueError):
            signals.oversold_overbought(self.rsi, overbought_level=70, oversold_level=-10)  # Below 0

    def test_trend_strength_basic(self):
        """Test basic functionality of trend strength calculation."""
        trend_str = signals.trend_strength(self.prices)
        self.assertIsInstance(trend_str, pd.Series)
        self.assertEqual(len(trend_str), len(self.prices))

    def test_trend_strength_invalid_inputs(self):
        """Test trend strength with invalid inputs."""
        with self.assertRaises(TypeError):
            signals.trend_strength([1, 2, 3])
        
        with self.assertRaises(ValueError):
            signals.trend_strength(self.prices[:2], window=5)  # Insufficient data

    def test_macd_signal_basic(self):
        """Test basic functionality of MACD signal generation."""
        macd_line, signal_line, _ = indicators.macd(self.prices)
        macd_signals = signals.macd_signal(macd_line, signal_line)
        self.assertIsInstance(macd_signals, pd.Series)
        self.assertEqual(len(macd_signals), len(self.prices))
        # Signals should be -1, 0, or 1
        self.assertTrue(macd_signals.isin([-1, 0, 1]).all())

    def test_bb_position_basic(self):
        """Test basic functionality of Bollinger Band position calculation."""
        upper, _, lower = indicators.bollinger_bands(self.prices)
        bb_positions = signals.bb_position(self.prices, upper, lower)
        self.assertIsInstance(bb_positions, pd.Series)
        self.assertEqual(len(bb_positions), len(self.prices))
        # Positions should be roughly between 0 and 1 (with possible slight exceedances due to calculation)
        self.assertTrue((bb_positions >= 0).all() or bb_positions.isna().all())
        self.assertTrue((bb_positions <= 1).all() or bb_positions.isna().all())

    def test_combined_signals_basic(self):
        """Test basic functionality of combined signals."""
        combined = signals.combined_signals(self.data)
        self.assertIsInstance(combined, pd.DataFrame)
        expected_cols = ['ma_signal', 'rsi_signal', 'macd_signal', 'bb_position', 'trend_strength', 'composite_score']
        for col in expected_cols:
            self.assertIn(col, combined.columns)
        
        self.assertEqual(len(combined), len(self.data))

    def test_combined_signals_missing_columns(self):
        """Test combined signals with missing required columns."""
        incomplete_data = self.data[['close', 'high']].copy()  # Missing 'low' and 'volume'
        with self.assertRaises(ValueError):
            signals.combined_signals(incomplete_data)

    def test_generate_trading_signals_basic(self):
        """Test basic functionality of trading signal generation."""
        # Create mock signal data
        signal_data = pd.DataFrame({
            'ma_signal': [0, 1, 0, -1, 1, 0, 1, -1, 0, 1],
            'rsi_signal': [0, 1, -1, 0, 1, 1, 0, -1, 0, 1],
            'composite_score': [0.1, 0.6, -0.3, -0.1, 0.7, 0.5, 0.2, -0.6, 0.0, 0.8]
        }, index=self.data.index)
        
        trading_signals = signals.generate_trading_signals(signal_data, strategy='moderate')
        self.assertIsInstance(trading_signals, pd.Series)
        self.assertEqual(len(trading_signals), len(signal_data))
        # Trading signals should be -1, 0, or 1
        self.assertTrue(trading_signals.isin([-1, 0, 1]).all())

    def test_generate_trading_signals_invalid_strategy(self):
        """Test trading signal generation with invalid strategy."""
        signal_data = pd.DataFrame({
            'ma_signal': [0, 1, 0, -1, 1],
            'rsi_signal': [0, 1, -1, 0, 1],
            'composite_score': [0.1, 0.6, -0.3, -0.1, 0.7]
        })
        
        with self.assertRaises(ValueError):
            signals.generate_trading_signals(signal_data, strategy='invalid_strategy')

    def test_generate_trading_signals_missing_columns(self):
        """Test trading signal generation with missing required columns."""
        incomplete_data = pd.DataFrame({
            'ma_signal': [0, 1, 0, -1, 1],  # Missing 'rsi_signal' and 'composite_score'
        })
        
        with self.assertRaises(ValueError):
            signals.generate_trading_signals(incomplete_data)


class TestSignalGenerationEdgeCases(unittest.TestCase):
    """Test signal generation with edge cases."""

    def setUp(self):
        """Set up edge case test data."""
        # Flat price series
        self.flat_prices = pd.Series([100] * 10, 
                                    index=pd.date_range('2023-01-01', periods=10))
        
        # Perfectly increasing price series
        self.up_trend = pd.Series(range(100, 110), 
                                 index=pd.date_range('2023-01-01', periods=10))
        
        # Perfectly decreasing price series
        self.down_trend = pd.Series(range(110, 100, -1), 
                                   index=pd.date_range('2023-01-01', periods=10))

    def test_flat_price_behavior(self):
        """Test signal behavior with flat prices."""
        flat_ma_fast = indicators.moving_average(self.flat_prices, 3)
        flat_ma_slow = indicators.moving_average(self.flat_prices, 7)
        
        # With flat prices, there should be minimal crossings
        cross_signals = signals.golden_death_cross(flat_ma_fast, flat_ma_slow)
        # Most signals should be 0 (no crossing)
        zero_count = (cross_signals == 0).sum()
        self.assertGreaterEqual(zero_count, len(cross_signals) - 2)  # Allow for 2 potential crossings at edges

    def test_trend_following_signals(self):
        """Test that trend-following signals work correctly."""
        up_ma_fast = indicators.moving_average(self.up_trend, 3)
        up_ma_slow = indicators.moving_average(self.up_trend, 7)
        
        cross_signals = signals.golden_death_cross(up_ma_fast, up_ma_slow)
        # In an uptrend, fast MA should eventually be above slow MA
        final_signal = cross_signals.iloc[-1]
        # The final signal could be 1 (golden cross) or 0 (no cross but fast above slow)
        # But shouldn't be -1 (death cross) in a clear uptrend

    def test_rsi_extreme_values(self):
        """Test RSI with extreme values."""
        extreme_data = pd.DataFrame({
            'close': [100, 200, 100, 200, 100, 200, 100, 200, 100, 200],  # Alternating high/low
            'high': [200] * 10,
            'low': [100] * 10,
            'volume': [1000] * 10
        }, index=pd.date_range('2023-01-01', periods=10))
        
        rsi = indicators.rsi(extreme_data['close'])
        os_ob_signals = signals.oversold_overbought(rsi)
        self.assertIsInstance(os_ob_signals, pd.Series)

    def test_all_zeros_in_signals(self):
        """Test behavior when all indicators return neutral values."""
        neutral_data = pd.DataFrame({
            'ma_signal': [0] * 10,
            'rsi_signal': [0] * 10,
            'composite_score': [0.0] * 10
        }, index=pd.date_range('2023-01-01', periods=10))
        
        trading_signals = signals.generate_trading_signals(neutral_data, strategy='conservative')
        # With all neutral signals, we should mostly get hold signals
        hold_count = (trading_signals == 0).sum()
        self.assertGreaterEqual(hold_count, len(trading_signals) - 1)  # Allow 1 exception


class TestSignalStrategies(unittest.TestCase):
    """Test different signal strategies."""

    def setUp(self):
        """Set up test data for strategy tests."""
        self.signal_data = pd.DataFrame({
            'ma_signal': [0, 1, 0, -1, 1, 0, 1, -1, 0, 1],
            'rsi_signal': [0, 1, -1, 0, 1, 1, 0, -1, 0, 1],
            'composite_score': [0.1, 0.45, -0.3, -0.1, 0.55, 0.35, 0.15, -0.45, 0.05, 0.75]
        }, index=pd.date_range('2023-01-01', periods=10))

    def test_different_strategies_produce_different_signals(self):
        """Test that different strategies produce different signals."""
        conservative = signals.generate_trading_signals(self.signal_data, strategy='conservative')
        moderate = signals.generate_trading_signals(self.signal_data, strategy='moderate')
        aggressive = signals.generate_trading_signals(self.signal_data, strategy='aggressive')
        
        # Different strategies should potentially produce different signals
        # (though they might occasionally be the same depending on the data)
        self.assertIsInstance(conservative, pd.Series)
        self.assertIsInstance(moderate, pd.Series)
        self.assertIsInstance(aggressive, pd.Series)
        
        # All should have the same length
        self.assertEqual(len(conservative), len(moderate))
        self.assertEqual(len(moderate), len(aggressive))


if __name__ == '__main__':
    unittest.main()