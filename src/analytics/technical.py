"""
Trader Dashboard V5 - Technical Analysis
=========================================
Technical indicators and market analysis functions.
"""

import logging
from typing import Tuple, Optional, Union

import numpy as np
import pandas as pd
from scipy.stats import percentileofscore

logger = logging.getLogger(__name__)


class TechnicalAnalyzer:
    """
    Provides technical analysis indicators and calculations.
    
    All methods are stateless and work with pandas Series/DataFrames.
    Uses vectorized operations for performance.
    """
    
    @staticmethod
    def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
        """
        Calculate Relative Strength Index (RSI).
        
        Args:
            series: Price series
            period: Lookback period (default 14)
            
        Returns:
            RSI series (0-100 scale)
        """
        if series.empty:
            return pd.Series(dtype=float)
            
        delta = series.diff()
        gain = delta.where(delta > 0, 0).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    @staticmethod
    def calculate_macd(
        series: pd.Series,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9
    ) -> Tuple[pd.Series, pd.Series]:
        """
        Calculate MACD (Moving Average Convergence Divergence).
        
        Args:
            series: Price series
            fast: Fast EMA period (default 12)
            slow: Slow EMA period (default 26)
            signal: Signal line period (default 9)
            
        Returns:
            Tuple of (macd_line, signal_line)
        """
        if series.empty:
            empty = pd.Series(dtype=float)
            return empty, empty
            
        ema_fast = series.ewm(span=fast, adjust=False).mean()
        ema_slow = series.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        
        return macd_line, signal_line
    
    @staticmethod
    def calculate_bollinger_bands(
        series: pd.Series,
        window: int = 20,
        num_std: float = 2.0
    ) -> Tuple[pd.Series, pd.Series]:
        """
        Calculate Bollinger Bands.
        
        Args:
            series: Price series
            window: Moving average window (default 20)
            num_std: Number of standard deviations (default 2)
            
        Returns:
            Tuple of (upper_band, lower_band)
        """
        if series.empty:
            empty = pd.Series(dtype=float)
            return empty, empty
            
        sma = series.rolling(window=window).mean()
        std = series.rolling(window=window).std()
        upper_band = sma + (std * num_std)
        lower_band = sma - (std * num_std)
        
        return upper_band, lower_band
    
    @staticmethod
    def calculate_sma(series: pd.Series, window: int) -> pd.Series:
        """
        Calculate Simple Moving Average.
        
        Args:
            series: Price series
            window: Moving average window
            
        Returns:
            SMA series
        """
        if series.empty:
            return pd.Series(dtype=float)
        return series.rolling(window=window).mean()
    
    @staticmethod
    def calculate_ema(series: pd.Series, span: int) -> pd.Series:
        """
        Calculate Exponential Moving Average.
        
        Args:
            series: Price series
            span: EMA span
            
        Returns:
            EMA series
        """
        if series.empty:
            return pd.Series(dtype=float)
        return series.ewm(span=span, adjust=False).mean()
    
    @staticmethod
    def calculate_percentile_rank(
        series: pd.Series,
        window: Optional[int] = None
    ) -> Tuple[float, float, float]:
        """
        Calculate percentile rank of the latest move.
        
        Args:
            series: Price series
            window: Optional rolling window (uses all history if None)
            
        Returns:
            Tuple of (current_return, signed_percentile, absolute_percentile)
        """
        if isinstance(series, pd.DataFrame):
            series = series.iloc[:, 0]
        
        returns = series.pct_change().dropna()
        if returns.empty:
            return 0.0, 0.0, 0.0
        
        current_return = returns.iloc[-1]
        if isinstance(current_return, pd.Series):
            current_return = current_return.iloc[0]
        
        history = returns.iloc[-window:] if window else returns
        
        pct_rank_signed = percentileofscore(history, current_return)
        pct_rank_abs = percentileofscore(history.abs(), abs(current_return))
        
        return float(current_return), pct_rank_signed, pct_rank_abs
    
    @staticmethod
    def calculate_z_score(series: pd.Series, window: int = 252) -> float:
        """
        Calculate Robust Z-Score using Median and MAD.
        
        Uses Median Absolute Deviation (MAD) instead of standard deviation
        for better handling of fat-tailed distributions.
        
        Args:
            series: Value series
            window: Rolling window for statistics
            
        Returns:
            Modified Z-score (0.6745 * (x - median) / MAD)
        """
        if series.empty:
            return 0.0
        
        series = series.dropna()
        if len(series) < window // 2:
            return 0.0
        
        # Calculate rolling median
        rolling_median = series.rolling(window).median()
        median = rolling_median.iloc[-1]
        
        # Calculate MAD (Median Absolute Deviation)
        deviations = (series - rolling_median).abs()
        mad = deviations.rolling(window).median().iloc[-1]
        
        current_value = series.iloc[-1]
        
        if mad == 0 or np.isnan(mad):
            return 0.0
        
        # Modified Z-Score: 0.6745 is the scaling factor for normal distribution
        return 0.6745 * (current_value - median) / mad
    
    @staticmethod
    def calculate_pr(series: pd.Series, window: int = 252) -> float:
        """
        Calculate Percentile Rank of current value.
        
        Args:
            series: Value series
            window: Lookback window
            
        Returns:
            Percentile rank (0-100)
        """
        if series.empty:
            return 0.0
        
        series = series.dropna()
        if len(series) == 0:
            return 0.0
        
        current_value = series.iloc[-1]
        history = series.tail(window)
        
        return percentileofscore(history, current_value)
    
    @staticmethod
    def calculate_returns(
        series: pd.Series,
        periods: int = 1,
        method: str = 'simple'
    ) -> pd.Series:
        """
        Calculate returns from price series.
        
        Args:
            series: Price series
            periods: Number of periods for return calculation
            method: 'simple' or 'log' returns
            
        Returns:
            Returns series
        """
        if series.empty:
            return pd.Series(dtype=float)
        
        if method == 'log':
            return np.log(series / series.shift(periods))
        else:
            return series.pct_change(periods)
    
    @staticmethod
    def calculate_volatility(
        series: pd.Series,
        window: int = 20,
        annualize: bool = True,
        trading_days: int = 252
    ) -> pd.Series:
        """
        Calculate rolling volatility.
        
        Args:
            series: Price series
            window: Rolling window
            annualize: Whether to annualize (default True)
            trading_days: Trading days per year (default 252)
            
        Returns:
            Volatility series
        """
        if series.empty:
            return pd.Series(dtype=float)
        
        returns = series.pct_change()
        vol = returns.rolling(window).std()
        
        if annualize:
            vol = vol * np.sqrt(trading_days)
        
        return vol


class MarketAnalyzer(TechnicalAnalyzer):
    """
    Extended analyzer with market-specific calculations.
    Inherits all technical analysis methods.
    """
    
    @staticmethod
    def calculate_correlation_matrix(
        df: pd.DataFrame,
        window: int = 90
    ) -> pd.DataFrame:
        """
        Calculate rolling correlation matrix on returns.
        
        Args:
            df: DataFrame with price columns
            window: Rolling window in days
            
        Returns:
            Correlation matrix
        """
        returns = df.pct_change().tail(window)
        return returns.corr()
    
    @staticmethod
    def calculate_relative_strength(
        series: pd.Series,
        periods: int = 21
    ) -> float:
        """
        Calculate relative strength (percentage change over periods).
        
        Args:
            series: Price series
            periods: Lookback periods
            
        Returns:
            Percentage change
        """
        if series.empty or len(series) < periods:
            return 0.0
        
        return series.pct_change(periods).iloc[-1] * 100
