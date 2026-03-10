"""
Trader Dashboard V5 - Data Manager
===================================
Centralized data fetching from multiple sources with smart caching.
"""

import io
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, Any

import numpy as np
import pandas as pd
import requests
import yfinance as yf

from ..config import config
from .cache import CacheManager

logger = logging.getLogger(__name__)


class DataManager:
    """
    Manages data fetching from Yahoo Finance, FRED, and other sources.
    
    Features:
    - Smart caching with incremental updates
    - Automatic stock split/dividend adjustments
    - Derived metrics calculation
    - Multiple data source integration
    """
    
    # Request timeout in seconds
    REQUEST_TIMEOUT = 15
    
    # Retry configuration
    MAX_RETRIES = 3
    RETRY_DELAY = 1  # seconds
    
    def __init__(self, cache_manager: Optional[CacheManager] = None):
        """
        Initialize DataManager.
        
        Args:
            cache_manager: Optional CacheManager instance. Creates default if not provided.
        """
        self.cache = cache_manager or CacheManager()
        self.yahoo_tickers = config.tickers.yahoo_tickers
        self.fred_tickers = config.tickers.fred_tickers
        
    def fetch_data(self, force_update: bool = False) -> Tuple[pd.DataFrame, str]:
        """
        Smart data fetching with caching strategy.
        
        Strategy:
        1. Check cache validity (< 15 min) -> Return cache
        2. Check for incremental vs full refresh (> 7 days)
        3. Fetch only missing data (incremental) or full history
        4. Atomic write to prevent corruption
        
        Args:
            force_update: If True, bypass cache and fetch fresh data
            
        Returns:
            Tuple of (DataFrame, source_description)
        """
        # Check cache first
        if not force_update and self.cache.is_valid():
            df = self.cache.load()
            if df is not None:
                logger.info("Returning cached data")
                return df, "Local Cache"
        
        # Determine update mode
        cache_df = None
        start_date = datetime(config.cache.history_start_year, 1, 1)
        mode = "Full Download"
        
        if not self.cache.needs_full_refresh():
            cache_df = self.cache.load()
            if cache_df is not None and not cache_df.empty:
                last_date = cache_df.index[-1].to_pydatetime()
                yesterday = datetime.now() - timedelta(days=1)
                
                if last_date.date() >= yesterday.date():
                    logger.info("Cache is up to date")
                    return cache_df, "Local Cache (Up to Date)"
                
                # Incremental mode: fetch from last date - 5 days overlap
                start_date = last_date - timedelta(days=5)
                mode = "Incremental Update"
                logger.info(f"Incremental update from {start_date.date()}")
        else:
            mode = "Full Download"
            logger.info(f"Full download from {start_date.date()}")
        
        # Perform download
        new_data = self._download_all_data(start_date)
        
        if new_data.empty:
            if cache_df is not None:
                logger.warning("Download failed, returning stale cache")
                return cache_df, "Cache (Download Failed)"
            return pd.DataFrame(), "Failed"
        
        # Merge with existing cache if incremental
        if mode == "Incremental Update" and cache_df is not None:
            combined_df = pd.concat([cache_df, new_data])
            combined_df = combined_df[~combined_df.index.duplicated(keep='last')]
            combined_df.sort_index(inplace=True)
            final_df = combined_df
            logger.info(f"Merged incremental data: {len(cache_df)} + {len(new_data)} -> {len(final_df)} rows")
        else:
            final_df = new_data
        
        # Calculate derived metrics
        final_df = self._calculate_derived_metrics(final_df)
        
        # Save to cache
        if self.cache.save(final_df):
            logger.info(f"Data fetch complete: {mode}")
        else:
            logger.warning("Failed to save cache, data may not persist")
        
        return final_df, mode
    
    def _download_all_data(self, start_date: datetime) -> pd.DataFrame:
        """
        Download data from all sources.
        
        Args:
            start_date: Start date for data fetch
            
        Returns:
            Combined DataFrame with all data
        """
        end_date = datetime.now()
        
        # Fetch from Yahoo Finance
        df_yahoo = self._fetch_yahoo_data(start_date, end_date)
        
        # Fetch from FRED
        df_fred = self._fetch_fred_data(start_date, end_date)
        
        # Combine datasets
        if df_yahoo.empty and df_fred.empty:
            return pd.DataFrame()
        
        if df_fred.empty:
            return df_yahoo
        
        if df_yahoo.empty:
            return df_fred
        
        # Outer join to preserve all data
        df_all = df_yahoo.join(df_fred, how='outer')
        
        # Ensure timezone-naive index
        if df_all.index.tz is not None:
            df_all.index = df_all.index.tz_localize(None)
        
        df_all.sort_index(inplace=True)
        df_all.ffill(inplace=True)  # Forward fill gaps
        
        return df_all
    
    def _fetch_yahoo_data(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        Fetch price data from Yahoo Finance.
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            DataFrame with Yahoo Finance data
        """
        try:
            logger.info(f"Fetching Yahoo Finance data: {len(self.yahoo_tickers)} tickers")
            
            raw_data = yf.download(
                list(self.yahoo_tickers.values()),
                start=start_date,
                end=end_date,
                progress=False,
                auto_adjust=True,
                group_by='ticker'
            )
            
            df = pd.DataFrame(index=raw_data.index)
            
            # Normalize timezone
            if df.index.tz is not None:
                df.index = df.index.tz_localize(None)
            
            # Extract close prices for each ticker
            for key, ticker in self.yahoo_tickers.items():
                try:
                    ticker_series = self._extract_ticker_series(raw_data, ticker)
                    if ticker_series is not None:
                        # Normalize timezone for this series
                        if ticker_series.index.tz is not None:
                            ticker_series.index = ticker_series.index.tz_localize(None)
                        df[key] = ticker_series
                        df[f"{key}_Adj"] = ticker_series
                    else:
                        df[key] = np.nan
                        df[f"{key}_Adj"] = np.nan
                except Exception as e:
                    logger.debug(f"Error extracting {key}: {e}")
                    df[key] = np.nan
                    df[f"{key}_Adj"] = np.nan
            
            logger.info(f"Yahoo Finance: {len(df)} rows, {len(df.columns)} columns")
            return df
            
        except Exception as e:
            logger.error(f"Yahoo Finance download error: {e}")
            return pd.DataFrame()
    
    def _extract_ticker_series(self, raw_data: pd.DataFrame, ticker: str) -> Optional[pd.Series]:
        """
        Extract Close price series from multi-level DataFrame.
        
        Args:
            raw_data: Raw yfinance download result
            ticker: Ticker symbol to extract
            
        Returns:
            Series of Close prices or None
        """
        if not isinstance(raw_data.columns, pd.MultiIndex):
            return raw_data.get('Close')
        
        # Try different column structures
        if ticker in raw_data.columns.levels[0]:
            return raw_data[ticker]['Close']
        elif ticker.upper() in raw_data.columns.levels[0]:
            return raw_data[ticker.upper()]['Close']
        
        # Single ticker case
        if raw_data.columns.nlevels == 2:
            try:
                return raw_data.droplevel(1, axis=1)['Close']
            except (KeyError, TypeError):
                pass
        
        return None
    
    def _fetch_fred_data(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        Fetch economic data from FRED.
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            DataFrame with FRED data
        """
        logger.info(f"Fetching FRED data: {len(self.fred_tickers)} series")
        
        frames = []
        failed_series = []
        
        for key, series_id in self.fred_tickers.items():
            df_series = self._fetch_single_fred_series(series_id, start_date, end_date)
            if not df_series.empty:
                df_series.rename(columns={series_id: key}, inplace=True)
                frames.append(df_series)
            else:
                failed_series.append(key)
        
        if failed_series:
            logger.warning(f"Failed to fetch FRED series: {', '.join(failed_series)}")
        
        if not frames:
            return pd.DataFrame()
        
        df_fred = pd.concat(frames, axis=1)
        
        # Calculate CPI YoY before resampling
        if 'CPI' in df_fred.columns:
            df_fred['CPI_YoY'] = df_fred['CPI'].pct_change(12) * 100
        
        # Normalize timezone
        if df_fred.index.tz is not None:
            df_fred.index = df_fred.index.tz_localize(None)
        
        logger.info(f"FRED: {len(df_fred)} rows, {len(df_fred.columns)} columns")
        return df_fred
    
    def _fetch_single_fred_series(
        self, 
        series_id: str, 
        start_date: datetime, 
        end_date: datetime
    ) -> pd.DataFrame:
        """
        Fetch a single FRED series via public CSV endpoint.
        
        Args:
            series_id: FRED series identifier
            start_date: Start date
            end_date: End date
            
        Returns:
            DataFrame with single series
        """
        url = (
            f"https://fred.stlouisfed.org/graph/fredgraph.csv"
            f"?id={series_id}"
            f"&cosd={start_date.strftime('%Y-%m-%d')}"
            f"&coed={end_date.strftime('%Y-%m-%d')}"
        )
        
        for attempt in range(self.MAX_RETRIES):
            try:
                response = requests.get(url, timeout=self.REQUEST_TIMEOUT)
                response.raise_for_status()
                
                df = pd.read_csv(io.StringIO(response.text))
                
                if df.shape[1] < 2:
                    return pd.DataFrame()
                
                df.columns = ["DATE", series_id]
                df["DATE"] = pd.to_datetime(df["DATE"], errors="coerce")
                df.set_index("DATE", inplace=True)
                
                # FRED uses '.' for missing values
                df[series_id] = pd.to_numeric(
                    df[series_id].replace(".", np.nan), 
                    errors="coerce"
                )
                
                return df
                
            except requests.exceptions.Timeout:
                logger.warning(f"FRED timeout ({series_id}), attempt {attempt + 1}/{self.MAX_RETRIES}")
            except requests.exceptions.RequestException as e:
                logger.debug(f"FRED request failed ({series_id}): {e}")
                break
            except Exception as e:
                logger.debug(f"FRED parsing failed ({series_id}): {e}")
                break
        
        return pd.DataFrame()
    
    def _calculate_derived_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate derived indicators from combined dataset.
        
        Args:
            df: Combined DataFrame
            
        Returns:
            DataFrame with additional derived columns
        """
        # MOVE Index handling (use proxy if official data unavailable)
        if 'MOVE' in df.columns:
            recent_move = df['MOVE'].tail(30)
            if recent_move.isnull().all() or (recent_move == 0).all():
                if 'TLT' in df.columns:
                    df['MOVE_Final'] = (
                        df['TLT'].pct_change()
                        .rolling(20).std() 
                        * np.sqrt(252) * 100
                    )
                    df['MOVE_Source'] = "Proxy (TLT Vol)"
                else:
                    df['MOVE_Final'] = 0
                    df['MOVE_Source'] = "N/A"
            else:
                df['MOVE_Final'] = df['MOVE']
                df['MOVE_Source'] = "Official (^MOVE)"
        
        # Credit Stress Ratio (IEF/HYG)
        if 'IEF' in df.columns and 'HYG' in df.columns:
            df['Credit_Stress_Ratio'] = df['IEF'] / df['HYG']
        
        # Gold/Silver Ratio
        if 'GOLD' in df.columns and 'SILVER' in df.columns:
            df['Gold_Silver_Ratio'] = df['GOLD'] / df['SILVER']
        
        # Liquidity Spread (CP - T-Bill)
        if 'CP_3M' in df.columns and 'TBILL_3M' in df.columns:
            df['Liquidity_Spread'] = df['CP_3M'] - df['TBILL_3M']
        
        # Reserve Scarcity (IORB - EFFR)
        if 'IORB' in df.columns and 'EFFR' in df.columns:
            df['IORB_EFFR_Spread'] = df['IORB'] - df['EFFR']
        
        return df
    
    def fetch_ticker_data(self, ticker: str) -> pd.DataFrame:
        """
        Fetch historical data for a single ticker (for Deep Dive).
        
        Args:
            ticker: Stock/ETF ticker symbol
            
        Returns:
            DataFrame with OHLCV data
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365 * 5)
        
        try:
            df = yf.download(
                ticker, 
                start=start_date, 
                end=end_date, 
                progress=False, 
                auto_adjust=False
            )
            
            # Handle MultiIndex columns
            if isinstance(df.columns, pd.MultiIndex):
                if ticker in df.columns.levels[0]:
                    df = df.xs(ticker, axis=1, level=0)
                elif len(df.columns.levels) > 1 and ticker in df.columns.levels[1]:
                    df = df.xs(ticker, axis=1, level=1)
                elif df.columns.nlevels == 2:
                    df = df.droplevel(1, axis=1)
            
            if df.empty or 'Close' not in df.columns:
                logger.warning(f"No data found for {ticker}")
                return pd.DataFrame()
            
            return df
            
        except Exception as e:
            logger.error(f"Error fetching {ticker}: {e}")
            return pd.DataFrame()
    
    def fetch_ticker_info(self, ticker: str) -> Dict[str, Any]:
        """
        Fetch fundamental info for a ticker.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Dictionary of ticker info
        """
        try:
            t = yf.Ticker(ticker)
            return t.info or {}
        except Exception as e:
            logger.debug(f"Error fetching info for {ticker}: {e}")
            return {}
    
    def fetch_fear_greed_index(self) -> Optional[Dict[str, Any]]:
        """
        Fetch CNN Fear & Greed Index data.
        
        Returns:
            Dictionary with fear/greed data or None
        """
        url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/91.0.4472.124 Safari/537.36"
            )
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            if 'fear_and_greed' in data:
                return data['fear_and_greed']
                
        except requests.exceptions.Timeout:
            logger.warning("Fear & Greed API timeout")
        except requests.exceptions.RequestException as e:
            logger.debug(f"Fear & Greed API error: {e}")
        except Exception as e:
            logger.debug(f"Fear & Greed parsing error: {e}")
        
        return None
    
    def get_last_update_time(self) -> str:
        """Get formatted last update time from cache."""
        return self.cache.get_last_update_time()
