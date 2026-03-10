"""
Trader Dashboard V5 - Risk Analysis
====================================
Advanced risk metrics and portfolio analytics.
"""

import logging
from typing import Dict, Optional, Any, Tuple

import numpy as np
import pandas as pd
from scipy.stats import skew, kurtosis, norm

from ..config import config

logger = logging.getLogger(__name__)


class RiskAnalyzer:
    """
    Provides institutional-grade risk analysis.
    
    Features:
    - Dual-Beta (Up/Down Market Analysis)
    - Cornish-Fisher VaR
    - Sharpe/Sortino Ratios
    - Maximum Drawdown
    """
    
    # Minimum sample requirements
    MIN_SAMPLES_BETA = 30
    MIN_SAMPLES_VAR = 60
    
    def __init__(self, risk_free_rate: Optional[float] = None):
        """
        Initialize RiskAnalyzer.
        
        Args:
            risk_free_rate: Annual risk-free rate (default from config)
        """
        self.risk_free_rate = risk_free_rate or config.risk.default_risk_free_rate
    
    def calculate_sharpe_ratio(
        self,
        series: pd.Series,
        risk_free_rate: Optional[float] = None,
        trading_days: int = 252
    ) -> float:
        """
        Calculate annualized Sharpe Ratio.
        
        Args:
            series: Price series
            risk_free_rate: Annual risk-free rate (uses instance default if None)
            trading_days: Trading days per year
            
        Returns:
            Annualized Sharpe Ratio
        """
        rf = risk_free_rate or self.risk_free_rate
        
        returns = series.pct_change().dropna()
        if returns.empty or len(returns) < 2:
            return 0.0
        
        # Daily risk-free rate
        daily_rf = rf / trading_days
        excess_returns = returns - daily_rf
        
        mean_excess = excess_returns.mean()
        std_dev = returns.std()
        
        if std_dev == 0 or np.isnan(std_dev):
            return 0.0
        
        return np.sqrt(trading_days) * mean_excess / std_dev
    
    def calculate_sortino_ratio(
        self,
        series: pd.Series,
        risk_free_rate: Optional[float] = None,
        trading_days: int = 252
    ) -> float:
        """
        Calculate annualized Sortino Ratio.
        
        Unlike Sharpe, Sortino only penalizes downside volatility.
        
        Args:
            series: Price series
            risk_free_rate: Annual risk-free rate
            trading_days: Trading days per year
            
        Returns:
            Annualized Sortino Ratio
        """
        rf = risk_free_rate or self.risk_free_rate
        
        returns = series.pct_change().dropna()
        if returns.empty or len(returns) < 2:
            return 0.0
        
        daily_rf = rf / trading_days
        excess_returns = returns - daily_rf
        
        mean_excess = excess_returns.mean()
        
        # Downside deviation (only negative returns)
        downside_returns = returns[returns < 0]
        if len(downside_returns) < 2:
            return 0.0
        
        downside_std = downside_returns.std()
        
        if downside_std == 0 or np.isnan(downside_std):
            return 0.0
        
        return np.sqrt(trading_days) * mean_excess / downside_std
    
    @staticmethod
    def calculate_max_drawdown(series: pd.Series) -> float:
        """
        Calculate Maximum Drawdown.
        
        Args:
            series: Price series
            
        Returns:
            Maximum drawdown as decimal (negative value)
        """
        if series.empty:
            return 0.0
        
        series = series.dropna()
        if len(series) < 2:
            return 0.0
        
        cummax = series.cummax()
        drawdown = (series - cummax) / cummax
        
        return drawdown.min()
    
    @staticmethod
    def calculate_drawdown_series(series: pd.Series) -> pd.Series:
        """
        Calculate drawdown time series.
        
        Args:
            series: Price series
            
        Returns:
            Drawdown series (negative values)
        """
        if series.empty:
            return pd.Series(dtype=float)
        
        cummax = series.cummax()
        return (series - cummax) / cummax
    
    def calculate_asymmetric_risk(
        self,
        target_series: pd.Series,
        benchmark_series: pd.Series,
        window: int = 252
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate Dual-Beta (Up/Down) and Capture Ratios.
        
        Uses log returns for mathematical rigor and separates market
        regimes by benchmark return sign.
        
        Args:
            target_series: Target asset price series
            benchmark_series: Benchmark price series (e.g., SPY)
            window: Lookback window in trading days
            
        Returns:
            Dictionary with risk metrics or None if insufficient data:
            - valid: Whether calculation succeeded
            - beta_plus: Up-market beta
            - beta_minus: Down-market beta
            - up_capture: Upside capture ratio
            - down_capture: Downside capture ratio
            - corr: Correlation coefficient
            - n_up: Number of up-market observations
            - n_down: Number of down-market observations
        """
        # Align data (strict inner join)
        df = pd.concat([target_series, benchmark_series], axis=1, join='inner').dropna()
        
        if len(df) < window + 1:
            logger.debug(f"Insufficient data for dual-beta: {len(df)} < {window + 1}")
            return None
        
        target = df.iloc[:, 0]
        bench = df.iloc[:, 1]
        
        # Log returns for mathematical rigor
        log_ret_target = np.log(target / target.shift(1)).dropna()
        log_ret_bench = np.log(bench / bench.shift(1)).dropna()
        
        # Use last 'window' periods
        r_target = log_ret_target.tail(window)
        r_bench = log_ret_bench.tail(window)
        
        if len(r_bench) < self.MIN_SAMPLES_BETA:
            logger.debug(f"Insufficient samples: {len(r_bench)} < {self.MIN_SAMPLES_BETA}")
            return None
        
        # Regime classification
        up_mask = r_bench > 0
        down_mask = r_bench <= 0
        
        r_target_up = r_target[up_mask]
        r_bench_up = r_bench[up_mask]
        r_target_down = r_target[down_mask]
        r_bench_down = r_bench[down_mask]
        
        n_up = len(r_bench_up)
        n_down = len(r_bench_down)
        
        # Statistical significance check
        if n_up < self.MIN_SAMPLES_BETA or n_down < self.MIN_SAMPLES_BETA:
            return {
                "valid": False,
                "n_up": n_up,
                "n_down": n_down,
                "msg": f"Insufficient samples (<{self.MIN_SAMPLES_BETA})"
            }
        
        # Dual-Beta Calculation: Beta = Cov(Asset, Bench) / Var(Bench)
        beta_plus = self._calculate_beta(r_target_up, r_bench_up)
        beta_minus = self._calculate_beta(r_target_down, r_bench_down)
        
        # Capture Ratios (Geometric)
        up_capture = self._calculate_capture_ratio(r_target_up, r_bench_up)
        down_capture = self._calculate_capture_ratio(r_target_down, r_bench_down)
        
        return {
            "valid": True,
            "beta_plus": beta_plus,
            "beta_minus": beta_minus,
            "up_capture": up_capture,
            "down_capture": down_capture,
            "n_up": n_up,
            "n_down": n_down,
            "corr": r_target.corr(r_bench)
        }
    
    @staticmethod
    def _calculate_beta(
        target_returns: pd.Series,
        bench_returns: pd.Series
    ) -> float:
        """Calculate beta from return series."""
        if len(target_returns) < 2:
            return np.nan
        
        cov = np.cov(target_returns, bench_returns)[0][1]
        var = np.var(bench_returns, ddof=1)
        
        if var <= 0:
            return np.nan
        
        return cov / var
    
    @staticmethod
    def _calculate_capture_ratio(
        target_returns: pd.Series,
        bench_returns: pd.Series
    ) -> float:
        """Calculate capture ratio from log returns."""
        # Convert back to arithmetic total return
        tr_target = np.exp(target_returns.sum()) - 1
        tr_bench = np.exp(bench_returns.sum()) - 1
        
        if tr_bench == 0:
            return np.nan
        
        return (tr_target / tr_bench) * 100
    
    @staticmethod
    def calculate_cornish_fisher_var(
        series: pd.Series,
        confidence: float = 0.95,
        window: int = 252
    ) -> Tuple[float, float, float, float]:
        """
        Calculate Cornish-Fisher Value at Risk.
        
        Adjusts the normal VaR estimate for skewness and kurtosis
        using the Cornish-Fisher expansion.
        
        Args:
            series: Price series
            confidence: Confidence level (default 0.95)
            window: Lookback window
            
        Returns:
            Tuple of (var, skewness, kurtosis, adjusted_z)
        """
        returns = series.pct_change().dropna().tail(window)
        
        if len(returns) < RiskAnalyzer.MIN_SAMPLES_VAR:
            return 0.0, 0.0, 0.0, 0.0
        
        # Calculate moments
        mu = returns.mean()
        sigma = returns.std()
        s = skew(returns)
        k = kurtosis(returns)  # Excess kurtosis (Fisher)
        
        # Z-score for confidence level
        z = norm.ppf(1 - confidence)
        
        # Cornish-Fisher Expansion
        # z_adj = z + (1/6)(z^2-1)S + (1/24)(z^3-3z)K - (1/36)(2z^3-5z)S^2
        z_adj = (
            z 
            + (1/6) * (z**2 - 1) * s 
            + (1/24) * (z**3 - 3*z) * k 
            - (1/36) * (2*z**3 - 5*z) * (s**2)
        )
        
        # VaR = -(mu + z_adj * sigma)
        var = -(mu + z_adj * sigma)
        
        return var, s, k, z_adj
    
    @staticmethod
    def calculate_information_ratio(
        target_series: pd.Series,
        benchmark_series: pd.Series,
        trading_days: int = 252
    ) -> float:
        """
        Calculate Information Ratio.
        
        Measures risk-adjusted excess return relative to benchmark.
        
        Args:
            target_series: Target asset price series
            benchmark_series: Benchmark price series
            trading_days: Trading days per year
            
        Returns:
            Annualized Information Ratio
        """
        target_returns = target_series.pct_change().dropna()
        bench_returns = benchmark_series.pct_change().dropna()
        
        # Align series
        common_idx = target_returns.index.intersection(bench_returns.index)
        if len(common_idx) < 2:
            return 0.0
        
        target_returns = target_returns.loc[common_idx]
        bench_returns = bench_returns.loc[common_idx]
        
        # Active returns
        active_returns = target_returns - bench_returns
        
        # Tracking error
        tracking_error = active_returns.std()
        
        if tracking_error == 0 or np.isnan(tracking_error):
            return 0.0
        
        mean_active = active_returns.mean()
        
        return np.sqrt(trading_days) * mean_active / tracking_error
    
    @staticmethod
    def detect_market_regime(df: pd.DataFrame) -> Dict[str, Any]:
        """
        Detect current market regime based on key indicators.
        
        Args:
            df: DataFrame with VIX, term structure, and credit data
            
        Returns:
            Dictionary with regime classification and indicators
        """
        regime = "NORMAL"
        signals = []
        
        # VIX level
        if 'VIX' in df.columns:
            vix = df['VIX'].dropna().iloc[-1] if not df['VIX'].dropna().empty else None
            if vix:
                if vix > 35:
                    signals.append(("VIX", "CRISIS", vix))
                    regime = "CRISIS"
                elif vix > 25:
                    signals.append(("VIX", "STRESS", vix))
                    if regime == "NORMAL":
                        regime = "STRESS"
                elif vix < 12:
                    signals.append(("VIX", "COMPLACENT", vix))
        
        # VIX Term Structure
        if 'VIX' in df.columns and 'VIX3M' in df.columns:
            vix = df['VIX'].dropna()
            vix3m = df['VIX3M'].dropna()
            idx = vix.index.intersection(vix3m.index)
            if not idx.empty:
                spread = (vix.loc[idx] - vix3m.loc[idx]).iloc[-1]
                if spread > 0:  # Backwardation
                    signals.append(("Term Structure", "INVERTED", spread))
                    if regime not in ["CRISIS"]:
                        regime = "STRESS"
        
        # High Yield Spreads
        if 'HY_OAS' in df.columns:
            hy_oas = df['HY_OAS'].dropna().iloc[-1] if not df['HY_OAS'].dropna().empty else None
            if hy_oas:
                if hy_oas > 8:
                    signals.append(("HY OAS", "CRISIS", hy_oas))
                    regime = "CRISIS"
                elif hy_oas > 5:
                    signals.append(("HY OAS", "ELEVATED", hy_oas))
        
        return {
            "regime": regime,
            "signals": signals,
            "description": {
                "NORMAL": "Standard market conditions",
                "STRESS": "Elevated risk indicators, caution advised",
                "CRISIS": "Severe market stress, defensive positioning recommended",
                "COMPLACENT": "Low volatility, potential for mean reversion"
            }.get(regime, "Unknown")
        }
    
    @staticmethod
    def calculate_position_size(
        account_equity: float,
        risk_per_trade: float,
        entry_price: float,
        stop_loss_price: float,
        var_adjustment: float = 1.0
    ) -> Dict[str, float]:
        """
        Calculate position size based on risk parameters.
        
        Args:
            account_equity: Total account value
            risk_per_trade: Risk per trade as decimal (e.g., 0.01 for 1%)
            entry_price: Entry price
            stop_loss_price: Stop loss price
            var_adjustment: VaR-based adjustment factor
            
        Returns:
            Dictionary with position sizing details
        """
        risk_amount = account_equity * risk_per_trade
        risk_per_share = abs(entry_price - stop_loss_price)
        
        if risk_per_share == 0:
            return {
                "shares": 0,
                "position_value": 0,
                "risk_amount": risk_amount,
                "error": "Stop loss equals entry price"
            }
        
        shares = int((risk_amount / risk_per_share) * var_adjustment)
        position_value = shares * entry_price
        
        return {
            "shares": shares,
            "position_value": position_value,
            "risk_amount": risk_amount,
            "position_pct": position_value / account_equity * 100 if account_equity > 0 else 0,
            "var_adjusted": var_adjustment != 1.0
        }
