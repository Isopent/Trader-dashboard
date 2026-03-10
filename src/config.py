"""
Trader Dashboard V5 - Configuration Module
===========================================
Centralized configuration management with environment variable support.
"""

import os
import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class CacheConfig:
    """Cache-related configuration."""
    file_path: str = "market_data_cache.csv"
    expiry_seconds: int = 900  # 15 minutes
    full_refresh_days: int = 7
    history_start_year: int = 2000


@dataclass
class RiskConfig:
    """Risk calculation configuration."""
    default_risk_free_rate: float = 0.04
    min_samples_for_beta: int = 30
    rolling_window_days: int = 252
    var_confidence: float = 0.95


@dataclass
class UIConfig:
    """UI-related configuration."""
    theme: str = "plotly_dark"
    default_time_range: str = "5Y"
    chart_height_default: int = 400
    chart_height_large: int = 600


@dataclass
class TickerConfig:
    """Asset ticker configuration."""
    # Yahoo Finance tickers
    yahoo_tickers: Dict[str, str] = field(default_factory=lambda: {
        # Equities
        "SPY": "SPY", "QQQ": "QQQ", "IWM": "IWM",
        # Volatility
        "VIX": "^VIX", "VIX3M": "^VIX3M", "VVIX": "^VVIX", "SKEW": "^SKEW",
        "VIX9D": "^VIX9D", "VIX1D": "^VIX1D",
        # Rates/Credit
        "MOVE": "^MOVE", "TLT": "TLT", "IEF": "IEF", "HYG": "HYG",
        # Commodities
        "GOLD": "GC=F", "SILVER": "SI=F", "OIL": "CL=F", "COPPER": "HG=F",
        # Forex
        "USDJPY": "JPY=X", "EURUSD": "EURUSD=X", "USDCHF": "CHF=X", "DX-Y": "DX-Y.NYB",
        # Crypto
        "BTC": "BTC-USD", "ETH": "ETH-USD",
        # S&P 500 Equal Weight
        "RSP": "RSP",
        # Sectors
        "XLK": "XLK", "XLF": "XLF", "XLE": "XLE", "XLV": "XLV", "XLY": "XLY",
        "XLP": "XLP", "XLI": "XLI", "XLB": "XLB", "XLRE": "XLRE", "XLC": "XLC", "XLU": "XLU",
        # Global Markets
        "EFA": "EFA", "VGK": "VGK", "EWJ": "EWJ",
        "EEM": "EEM", "MCHI": "MCHI", "INDA": "INDA", "EWY": "EWY", "EWZ": "EWZ",
        # Risk-Free Rate
        "RF_RATE": "^IRX"
    })
    
    # FRED tickers
    fred_tickers: Dict[str, str] = field(default_factory=lambda: {
        # Financial Stress Indices
        "STLFSI": "STLFSI4", "NFCI": "NFCI",
        # Treasury Yields
        "US2Y": "DGS2", "US10Y": "DGS10", "US20Y": "DGS20", "US30Y": "DGS30",
        # Macro
        "CPI": "CPIAUCSL", "UNRATE": "UNRATE", "FEDFUNDS": "FEDFUNDS",
        # Credit
        "HY_OAS": "BAMLH0A0HYM2",
        # Liquidity
        "CP_3M": "CPF3M", "TBILL_3M": "DTB3",
        # Fed Balance Sheet
        "FED_ASSETS": "WALCL", "FED_CUSTODY": "WSHOMCB",
        # Rates
        "SOFR": "SOFR", "IORB": "IORB", "EFFR": "EFFR",
        # Inflation
        "T10YIE": "T10YIE", "REAL_YIELD_10Y": "DFII10",
        # Japan
        "JPN_RATE": "IRSTCI01JPM156N", "JPN_10Y": "IRLTLT01JPM156N",
        "JPN_UNRATE": "LRUN64TTJPM156S", "JPN_M2": "MYAGM2JPM189N"
    })


@dataclass
class AppConfig:
    """Main application configuration."""
    cache: CacheConfig = field(default_factory=CacheConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    tickers: TickerConfig = field(default_factory=TickerConfig)
    
    # App metadata
    app_name: str = "Alpha Trader 戰情室"
    version: str = "5.0.0"
    
    @classmethod
    def load_from_env(cls) -> "AppConfig":
        """Load configuration with environment variable overrides."""
        config = cls()
        
        # Override from environment variables if present
        if os.getenv("CACHE_EXPIRY_SECONDS"):
            config.cache.expiry_seconds = int(os.getenv("CACHE_EXPIRY_SECONDS"))
        if os.getenv("FULL_REFRESH_DAYS"):
            config.cache.full_refresh_days = int(os.getenv("FULL_REFRESH_DAYS"))
        if os.getenv("RISK_FREE_RATE"):
            config.risk.default_risk_free_rate = float(os.getenv("RISK_FREE_RATE"))
            
        logger.info(f"Configuration loaded: cache_expiry={config.cache.expiry_seconds}s")
        return config


class UserSettings:
    """
    User settings persistence manager.
    Handles saving/loading user preferences to JSON file.
    """
    
    CONFIG_FILE = "user_config.json"
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = Path(config_path or self.CONFIG_FILE)
        self._cache: Optional[Dict] = None
    
    def load(self) -> Dict:
        """Load user settings from JSON file."""
        if self._cache is not None:
            return self._cache
            
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self._cache = json.load(f)
                    logger.debug(f"Loaded user settings from {self.config_path}")
                    return self._cache
            except json.JSONDecodeError as e:
                logger.error(f"User config file corrupted: {e}")
                return {}
            except PermissionError:
                logger.error(f"Permission denied reading {self.config_path}")
                return {}
        return {}
    
    def save(self, settings: Dict) -> bool:
        """Save user settings to JSON file."""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2)
            self._cache = settings
            logger.debug(f"Saved user settings to {self.config_path}")
            return True
        except PermissionError:
            logger.error(f"Permission denied writing {self.config_path}")
            return False
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            return False
    
    def get_range_setting(self, chart_key: str, default: str = "5Y") -> str:
        """Get saved time range setting for a chart."""
        settings = self.load()
        return settings.get(f"range_{chart_key}", default)
    
    def set_range_setting(self, chart_key: str, value: str) -> bool:
        """Save time range setting for a chart."""
        settings = self.load()
        settings[f"range_{chart_key}"] = value
        return self.save(settings)
    
    def clear_cache(self) -> None:
        """Clear the in-memory cache."""
        self._cache = None


# Global configuration instance
config = AppConfig.load_from_env()
user_settings = UserSettings()
