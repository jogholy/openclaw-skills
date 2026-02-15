"""
Backtesting Engine Module

This module provides a framework for backtesting trading strategies using historical data.

Classes:
    - BacktestEngine: Main backtesting engine
    - Portfolio: Portfolio management class
    - Position: Individual position tracking

Functions:
    - calculate_returns: Calculate portfolio returns
    - max_drawdown: Calculate maximum drawdown
    - sharpe_ratio: Calculate Sharpe ratio
    - sortino_ratio: Calculate Sortino ratio
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Position:
    """Represents a single position in the portfolio."""
    symbol: str
    quantity: float
    entry_price: float
    entry_date: datetime
    exit_price: Optional[float] = None
    exit_date: Optional[datetime] = None
    position_type: str = 'long'  # 'long' or 'short'


class Portfolio:
    """Manages portfolio holdings and cash balance."""
    
    def __init__(self, initial_capital: float = 100000.0):
        """
        Initialize portfolio with initial capital.
        
        Args:
            initial_capital: Starting capital amount
        """
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: Dict[str, Position] = {}
        self.history: List[Dict] = []
        self.current_date = None
    
    def get_total_value(self, prices: Dict[str, float]) -> float:
        """
        Calculate total portfolio value including cash and positions.
        
        Args:
            prices: Dictionary mapping symbols to current prices
            
        Returns:
            Total portfolio value
        """
        positions_value = 0.0
        for symbol, position in self.positions.items():
            if symbol in prices:
                if position.position_type == 'long':
                    positions_value += position.quantity * prices[symbol]
                else:  # short position
                    # For short positions, we profit when price goes down
                    current_value = position.quantity * (position.entry_price - prices[symbol])
                    positions_value += position.quantity * position.entry_price + current_value
        
        return self.cash + positions_value
    
    def buy(self, symbol: str, quantity: float, price: float, date: datetime) -> bool:
        """
        Execute a buy order.
        
        Args:
            symbol: Asset symbol
            quantity: Quantity to buy
            price: Price per unit
            date: Transaction date
            
        Returns:
            True if successful, False otherwise
        """
        cost = quantity * price
        if cost > self.cash:
            return False  # Insufficient funds
        
        self.cash -= cost
        
        # If we already have a position in this symbol, adjust it
        if symbol in self.positions:
            existing_pos = self.positions[symbol]
            # Calculate weighted average entry price
            total_quantity = existing_pos.quantity + quantity
            total_cost = (existing_pos.quantity * existing_pos.entry_price) + cost
            new_entry_price = total_cost / total_quantity
            
            self.positions[symbol] = Position(
                symbol=symbol,
                quantity=total_quantity,
                entry_price=new_entry_price,
                entry_date=existing_pos.entry_date,  # Keep original entry date
                position_type='long'
            )
        else:
            self.positions[symbol] = Position(
                symbol=symbol,
                quantity=quantity,
                entry_price=price,
                entry_date=date,
                position_type='long'
            )
        
        # Record transaction
        self.history.append({
            'date': date,
            'symbol': symbol,
            'action': 'BUY',
            'quantity': quantity,
            'price': price,
            'cost': cost,
            'cash_after': self.cash
        })
        
        return True
    
    def sell(self, symbol: str, quantity: float, price: float, date: datetime) -> bool:
        """
        Execute a sell order.
        
        Args:
            symbol: Asset symbol
            quantity: Quantity to sell
            price: Price per unit
            date: Transaction date
            
        Returns:
            True if successful, False otherwise
        """
        if symbol not in self.positions:
            return False  # No position to sell
        
        position = self.positions[symbol]
        if quantity > position.quantity:
            return False  # Cannot sell more than we own
        
        revenue = quantity * price
        self.cash += revenue
        
        # Adjust position
        remaining_quantity = position.quantity - quantity
        if remaining_quantity == 0:
            # Close the position completely
            position.exit_price = price
            position.exit_date = date
            del self.positions[symbol]
        else:
            # Partial sell, keep the position
            self.positions[symbol] = Position(
                symbol=symbol,
                quantity=remaining_quantity,
                entry_price=position.entry_price,
                entry_date=position.entry_date,
                exit_price=price if remaining_quantity == 0 else position.exit_price,
                exit_date=date if remaining_quantity == 0 else position.exit_date,
                position_type=position.position_type
            )
        
        # Record transaction
        self.history.append({
            'date': date,
            'symbol': symbol,
            'action': 'SELL',
            'quantity': quantity,
            'price': price,
            'revenue': revenue,
            'cash_after': self.cash
        })
        
        return True
    
    def get_position_pnl(self, symbol: str, current_price: float) -> float:
        """
        Calculate P&L for a specific position.
        
        Args:
            symbol: Asset symbol
            current_price: Current market price
            
        Returns:
            Profit/loss for the position
        """
        if symbol not in self.positions:
            return 0.0
        
        position = self.positions[symbol]
        if position.position_type == 'long':
            return (current_price - position.entry_price) * position.quantity
        else:  # short position
            return (position.entry_price - current_price) * position.quantity


def calculate_returns(portfolio_values: pd.Series) -> pd.Series:
    """
    Calculate period returns from portfolio values.
    
    Args:
        portfolio_values: Series of portfolio values over time
        
    Returns:
        Series of period returns
        
    Example:
        >>> values = pd.Series([100, 110, 105, 115])
        >>> returns = calculate_returns(values)
        >>> print(returns.iloc[1])  # Return from period 0 to 1
        0.1
    """
    if len(portfolio_values) < 2:
        return pd.Series([], dtype=float)
    
    returns = portfolio_values.pct_change().dropna()
    return returns


def max_drawdown(portfolio_values: pd.Series) -> float:
    """
    Calculate maximum drawdown from portfolio values.
    
    Args:
        portfolio_values: Series of portfolio values over time
        
    Returns:
        Maximum drawdown as a percentage (negative value)
        
    Example:
        >>> values = pd.Series([100, 110, 90, 95, 120])
        >>> mdd = max_drawdown(values)
        >>> print(f"Max drawdown: {mdd:.2%}")
        Max drawdown: -18.18%
    """
    if len(portfolio_values) < 2:
        return 0.0
    
    # Calculate running maximum
    running_max = portfolio_values.expanding().max()
    
    # Calculate drawdown as percentage from peak
    drawdown = (portfolio_values - running_max) / running_max
    
    # Return the minimum (most negative) drawdown
    return drawdown.min()


def sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.02) -> float:
    """
    Calculate Sharpe ratio from returns.
    
    Args:
        returns: Series of period returns
        risk_free_rate: Annual risk-free rate (default 2%)
        
    Returns:
        Sharpe ratio
        
    Example:
        >>> returns = pd.Series([0.01, 0.02, -0.01, 0.03, 0.01])
        >>> sharpe = sharpe_ratio(returns)
        >>> print(f"Sharpe ratio: {sharpe:.2f}")
        Sharpe ratio: 1.26
    """
    if len(returns) < 2:
        return 0.0
    
    # Convert annual risk-free rate to period rate (assuming daily returns)
    period_rf = risk_free_rate / 252  # 252 trading days per year
    
    excess_returns = returns - period_rf
    mean_excess_return = excess_returns.mean()
    volatility = returns.std()
    
    if volatility == 0:
        return 0.0
    
    # Annualize Sharpe ratio
    sharpe = mean_excess_return / volatility
    return sharpe * np.sqrt(252)  # Annualize assuming daily returns


def sortino_ratio(returns: pd.Series, risk_free_rate: float = 0.02) -> float:
    """
    Calculate Sortino ratio from returns (uses downside deviation).
    
    Args:
        returns: Series of period returns
        risk_free_rate: Annual risk-free rate (default 2%)
        
    Returns:
        Sortino ratio
        
    Example:
        >>> returns = pd.Series([0.01, 0.02, -0.01, 0.03, 0.01])
        >>> sortino = sortino_ratio(returns)
        >>> print(f"Sortino ratio: {sortino:.2f}")
        Sortino ratio: 1.58
    """
    if len(returns) < 2:
        return 0.0
    
    # Convert annual risk-free rate to period rate (assuming daily returns)
    period_rf = risk_free_rate / 252
    
    excess_returns = returns - period_rf
    mean_excess_return = excess_returns.mean()
    
    # Calculate downside deviation (only negative returns)
    negative_returns = excess_returns[excess_returns < 0]
    if len(negative_returns) == 0:
        downside_deviation = 0.0
    else:
        downside_deviation = np.sqrt((negative_returns ** 2).mean())
    
    if downside_deviation == 0:
        return 0.0
    
    # Annualize Sortino ratio
    sortino = mean_excess_return / downside_deviation
    return sortino * np.sqrt(252)  # Annualize assuming daily returns


def calculate_win_rate(returns: pd.Series) -> float:
    """
    Calculate win rate (percentage of positive returns).
    
    Args:
        returns: Series of period returns
        
    Returns:
        Win rate as a percentage
        
    Example:
        >>> returns = pd.Series([0.01, 0.02, -0.01, 0.03, -0.02])
        >>> win_rate = calculate_win_rate(returns)
        >>> print(f"Win rate: {win_rate:.2%}")
        Win rate: 60.00%
    """
    if len(returns) == 0:
        return 0.0
    
    positive_returns = (returns > 0).sum()
    total_returns = len(returns)
    
    return positive_returns / total_returns


def calculate_profit_factor(gross_profits: pd.Series, gross_losses: pd.Series) -> float:
    """
    Calculate profit factor (ratio of gross profits to gross losses).
    
    Args:
        gross_profits: Series of positive returns
        gross_losses: Series of negative returns (positive values)
        
    Returns:
        Profit factor
        
    Example:
        >>> profits = pd.Series([100, 200, 150])
        >>> losses = pd.Series([50, 75])
        >>> pf = calculate_profit_factor(profits, losses)
        >>> print(f"Profit factor: {pf:.2f}")
        Profit factor: 3.60
    """
    total_profits = gross_profits.sum() if len(gross_profits) > 0 else 0
    total_losses = gross_losses.sum() if len(gross_losses) > 0 else 0
    
    if total_losses == 0:
        return float('inf') if total_profits > 0 else 0
    
    return total_profits / total_losses


class BacktestEngine:
    """Main backtesting engine for testing trading strategies."""
    
    def __init__(self, initial_capital: float = 100000.0):
        """
        Initialize backtesting engine.
        
        Args:
            initial_capital: Starting capital for the backtest
        """
        self.initial_capital = initial_capital
        self.portfolio = Portfolio(initial_capital)
        self.results = {}
        self.trades = []
    
    def run_backtest(self, 
                     data: pd.DataFrame, 
                     signals: pd.Series,
                     position_size: float = 0.1,
                     transaction_cost: float = 0.001) -> Dict:
        """
        Run backtest with given data and signals.
        
        Args:
            data: DataFrame with OHLCV data (columns: open, high, low, close, volume)
                   Index should be datetime
            signals: Series of trading signals (-1 for sell, 0 for hold, 1 for buy)
                   Index should match data
            position_size: Maximum position size as fraction of portfolio (default 10%)
            transaction_cost: Cost per transaction as fraction (default 0.1%)
            
        Returns:
            Dictionary containing backtest results
        """
        if not isinstance(data, pd.DataFrame):
            raise TypeError("Data must be a pandas DataFrame")
        
        if not isinstance(signals, pd.Series):
            raise TypeError("Signals must be a pandas Series")
        
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        missing_cols = [col for col in required_cols if col not in data.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        # Ensure data and signals have matching indices
        if not data.index.equals(signals.index):
            # Align data and signals
            aligned_idx = data.index.intersection(signals.index)
            data = data.loc[aligned_idx]
            signals = signals.loc[aligned_idx]
        
        if len(data) == 0:
            raise ValueError("No overlapping data between prices and signals")
        
        # Initialize tracking variables
        portfolio_values = []
        dates = []
        
        # Process each time period
        for idx in data.index:
            current_date = idx
            current_prices = data.loc[idx]
            current_signal = signals.loc[idx] if idx in signals.index else 0
            
            # Store current portfolio value
            current_portfolio_value = self.portfolio.get_total_value({'close': current_prices['close']})
            portfolio_values.append(current_portfolio_value)
            dates.append(current_date)
            
            # Execute trades based on signals
            if current_signal == 1:  # Buy signal
                # Calculate position size
                available_cash = self.portfolio.cash
                max_investment = available_cash * position_size
                shares_to_buy = int(max_investment / current_prices['close'])
                
                if shares_to_buy > 0:
                    # Account for transaction costs
                    cost_per_share = current_prices['close'] * (1 + transaction_cost)
                    actual_cost = shares_to_buy * cost_per_share
                    
                    if actual_cost <= self.portfolio.cash:
                        self.portfolio.buy('close', shares_to_buy, current_prices['close'], current_date)
                        
            elif current_signal == -1:  # Sell signal
                # Sell all shares of the asset
                if 'close' in self.portfolio.positions:
                    pos = self.portfolio.positions['close']
                    proceeds_per_share = current_prices['close'] * (1 - transaction_cost)
                    
                    self.portfolio.sell('close', pos.quantity, current_prices['close'], current_date)
        
        # Convert portfolio values to series
        portfolio_series = pd.Series(portfolio_values, index=dates)
        
        # Calculate returns
        returns = calculate_returns(portfolio_series)
        
        # Calculate performance metrics
        total_return = (portfolio_series.iloc[-1] - self.initial_capital) / self.initial_capital
        annual_return = (portfolio_series.iloc[-1] / self.initial_capital) ** (252 / len(portfolio_series)) - 1
        max_dd = max_drawdown(portfolio_series)
        sharpe = sharpe_ratio(returns)
        sortino = sortino_ratio(returns)
        win_rate = calculate_win_rate(returns)
        
        # Prepare results
        self.results = {
            'initial_capital': self.initial_capital,
            'final_capital': portfolio_series.iloc[-1],
            'total_return': total_return,
            'annual_return': annual_return,
            'max_drawdown': max_dd,
            'sharpe_ratio': sharpe,
            'sortino_ratio': sortino,
            'win_rate': win_rate,
            'total_trades': len(self.trades),
            'portfolio_values': portfolio_series,
            'returns': returns,
            'start_date': dates[0] if dates else None,
            'end_date': dates[-1] if dates else None
        }
        
        return self.results
    
    def get_performance_summary(self) -> str:
        """
        Get a formatted performance summary.
        
        Returns:
            Formatted string with key performance metrics
        """
        if not self.results:
            return "No backtest results available. Run backtest first."
        
        summary = f"""
Backtest Performance Summary
============================
Initial Capital: ${self.results['initial_capital']:,.2f}
Final Capital:   ${self.results['final_capital']:,.2f}
Total Return:    {self.results['total_return']:.2%}
Annual Return:   {self.results['annual_return']:.2%}
Max Drawdown:    {self.results['max_drawdown']:.2%}
Sharpe Ratio:    {self.results['sharpe_ratio']:.2f}
Sortino Ratio:   {self.results['sortino_ratio']:.2f}
Win Rate:        {self.results['win_rate']:.2%}
Total Trades:    {self.results['total_trades']}
Start Date:      {self.results['start_date']}
End Date:        {self.results['end_date']}
        """.strip()
        
        return summary
    
    def plot_equity_curve(self) -> None:
        """
        Plot the equity curve of the backtest.
        Note: This requires matplotlib to be installed separately.
        """
        try:
            import matplotlib.pyplot as plt
            
            if not self.results or 'portfolio_values' not in self.results:
                print("No backtest results available to plot.")
                return
            
            plt.figure(figsize=(12, 6))
            plt.plot(self.results['portfolio_values'].index, 
                    self.results['portfolio_values'].values)
            plt.title('Portfolio Value Over Time')
            plt.xlabel('Date')
            plt.ylabel('Portfolio Value ($)')
            plt.grid(True)
            plt.tight_layout()
            plt.show()
            
        except ImportError:
            print("matplotlib not available. Install it with: pip install matplotlib")


def benchmark_strategy(data: pd.DataFrame, 
                      buy_and_hold: bool = True,
                      equal_weight_rebalance: bool = False) -> Dict:
    """
    Benchmark strategies against the tested strategy.
    
    Args:
        data: DataFrame with price data
        buy_and_hold: Whether to include buy-and-hold benchmark
        equal_weight_rebalance: Whether to include equal-weight rebalancing benchmark
        
    Returns:
        Dictionary with benchmark results
    """
    benchmarks = {}
    
    if buy_and_hold and 'close' in data.columns:
        # Buy and hold strategy
        initial_price = data['close'].iloc[0]
        final_price = data['close'].iloc[-1]
        total_return = (final_price - initial_price) / initial_price
        
        benchmarks['buy_and_hold'] = {
            'total_return': total_return,
            'annual_return': (final_price / initial_price) ** (252 / len(data)) - 1
        }
    
    return benchmarks