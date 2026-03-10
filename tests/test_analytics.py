"""
Trader Dashboard V5 - Test Suite
=================================
Unit tests for core modules.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add src to path
import sys
sys.path.insert(0, '..')

from src.analytics.technical import TechnicalAnalyzer
from src.analytics.risk import RiskAnalyzer


class TestTechnicalAnalyzer:
    """Tests for TechnicalAnalyzer class."""
    
    @pytest.fixture
    def sample_series(self):
        """Create sample price series for testing."""
        dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
        prices = 100 + np.cumsum(np.random.randn(100) * 0.5)
        return pd.Series(prices, index=dates)
    
    def test_rsi_range(self, sample_series):
        """RSI should be between 0 and 100."""
        rsi = TechnicalAnalyzer.calculate_rsi(sample_series)
        valid_rsi = rsi.dropna()
        assert (valid_rsi >= 0).all()
        assert (valid_rsi <= 100).all()
    
    def test_macd_returns_tuple(self, sample_series):
        """MACD should return tuple of two series."""
        macd, signal = TechnicalAnalyzer.calculate_macd(sample_series)
        assert isinstance(macd, pd.Series)
        assert isinstance(signal, pd.Series)
        assert len(macd) == len(sample_series)
    
    def test_bollinger_bands(self, sample_series):
        """Upper band should be above lower band."""
        upper, lower = TechnicalAnalyzer.calculate_bollinger_bands(sample_series)
        valid_idx = upper.dropna().index.intersection(lower.dropna().index)
        assert (upper.loc[valid_idx] >= lower.loc[valid_idx]).all()
    
    def test_empty_series_handling(self):
        """Should handle empty series gracefully."""
        empty = pd.Series(dtype=float)
        rsi = TechnicalAnalyzer.calculate_rsi(empty)
        assert rsi.empty
    
    def test_z_score(self, sample_series):
        """Z-score should be reasonable values."""
        z = TechnicalAnalyzer.calculate_z_score(sample_series.tail(300))
        assert isinstance(z, float)
        assert not np.isnan(z) or len(sample_series) < 126


class TestRiskAnalyzer:
    """Tests for RiskAnalyzer class."""
    
    @pytest.fixture
    def price_series(self):
        """Create sample price series."""
        dates = pd.date_range(start='2022-01-01', periods=300, freq='D')
        prices = 100 * np.exp(np.cumsum(np.random.randn(300) * 0.01))
        return pd.Series(prices, index=dates)
    
    @pytest.fixture
    def risk_analyzer(self):
        return RiskAnalyzer()
    
    def test_sharpe_ratio(self, risk_analyzer, price_series):
        """Sharpe ratio should be a finite number."""
        sharpe = risk_analyzer.calculate_sharpe_ratio(price_series)
        assert isinstance(sharpe, float)
        assert np.isfinite(sharpe)
    
    def test_sortino_ratio(self, risk_analyzer, price_series):
        """Sortino ratio should be a finite number."""
        sortino = risk_analyzer.calculate_sortino_ratio(price_series)
        assert isinstance(sortino, float)
        assert np.isfinite(sortino)
    
    def test_max_drawdown_negative(self, risk_analyzer, price_series):
        """Max drawdown should be non-positive."""
        mdd = risk_analyzer.calculate_max_drawdown(price_series)
        assert mdd <= 0
    
    def test_cornish_fisher_var(self, price_series):
        """VaR should return 4 values."""
        var, skew, kurt, z_adj = RiskAnalyzer.calculate_cornish_fisher_var(price_series)
        assert isinstance(var, float)
        assert isinstance(skew, float)
        assert isinstance(kurt, float)
    
    def test_dual_beta_insufficient_data(self, risk_analyzer):
        """Should return None for insufficient data."""
        short_series = pd.Series([100, 101, 102])
        result = risk_analyzer.calculate_asymmetric_risk(short_series, short_series)
        assert result is None
    
    def test_market_regime_detection(self):
        """Should detect market regime from data."""
        df = pd.DataFrame({
            'VIX': [25],
            'VIX3M': [22],
            'HY_OAS': [4.5]
        }, index=[datetime.now()])
        
        regime = RiskAnalyzer.detect_market_regime(df)
        assert 'regime' in regime
        assert regime['regime'] in ['NORMAL', 'STRESS', 'CRISIS', 'COMPLACENT']


class TestPositionSizing:
    """Tests for position sizing calculator."""
    
    def test_position_size_calculation(self):
        """Should calculate correct position size."""
        result = RiskAnalyzer.calculate_position_size(
            account_equity=100000,
            risk_per_trade=0.01,  # 1%
            entry_price=50,
            stop_loss_price=48
        )
        
        assert 'shares' in result
        assert result['shares'] > 0
        assert result['risk_amount'] == 1000  # 1% of 100k
    
    def test_zero_stop_loss_handling(self):
        """Should handle zero stop loss gracefully."""
        result = RiskAnalyzer.calculate_position_size(
            account_equity=100000,
            risk_per_trade=0.01,
            entry_price=50,
            stop_loss_price=50  # Same as entry
        )
        
        assert result['shares'] == 0
        assert 'error' in result


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
