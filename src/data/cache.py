"""
Trader Dashboard V5 - Cache Manager
====================================
Handles data caching with atomic writes and validation.
"""

import os
import time
import logging
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime

import pandas as pd

from ..config import config

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Manages CSV cache for market data with atomic writes and validation.
    
    Features:
    - Atomic file writes (temp file + rename) to prevent corruption
    - Configurable expiry time and full refresh intervals
    - History validation to ensure complete data
    """
    
    def __init__(self, cache_path: Optional[str] = None):
        """
        Initialize cache manager.
        
        Args:
            cache_path: Path to cache file. Uses config default if not provided.
        """
        self.cache_path = Path(cache_path or config.cache.file_path)
        self.expiry_seconds = config.cache.expiry_seconds
        self.full_refresh_days = config.cache.full_refresh_days
        self.history_start_year = config.cache.history_start_year
    
    def is_valid(self) -> bool:
        """
        Check if cache exists and is within expiry time.
        
        Returns:
            True if cache is valid and fresh, False otherwise.
        """
        if not self.cache_path.exists():
            logger.debug("Cache file does not exist")
            return False
            
        try:
            last_modified = os.path.getmtime(self.cache_path)
            age_seconds = time.time() - last_modified
            is_fresh = age_seconds < self.expiry_seconds
            
            if is_fresh:
                logger.debug(f"Cache is fresh (age: {age_seconds:.0f}s < {self.expiry_seconds}s)")
            else:
                logger.debug(f"Cache is stale (age: {age_seconds:.0f}s >= {self.expiry_seconds}s)")
                
            return is_fresh
        except OSError as e:
            logger.error(f"Error checking cache validity: {e}")
            return False
    
    def needs_full_refresh(self) -> bool:
        """
        Check if cache requires a full data refresh.
        
        Returns:
            True if cache is older than full_refresh_days or has incomplete history.
        """
        if not self.cache_path.exists():
            return True
            
        try:
            # Check file age
            file_age_days = (time.time() - os.path.getmtime(self.cache_path)) / 86400
            if file_age_days >= self.full_refresh_days:
                logger.info(f"Cache file age ({file_age_days:.1f} days) exceeds refresh threshold")
                return True
            
            # Check if history starts too late
            df = self.load()
            if df is not None and not df.empty:
                first_date = df.index[0].to_pydatetime()
                if first_date.year > self.history_start_year:
                    logger.info(f"Cache history starts at {first_date.year}, need backfill to {self.history_start_year}")
                    return True
                    
            return False
        except Exception as e:
            logger.error(f"Error checking full refresh requirement: {e}")
            return True
    
    def load(self) -> Optional[pd.DataFrame]:
        """
        Load cached data from file.
        
        Returns:
            DataFrame if cache exists and is valid, None otherwise.
        """
        if not self.cache_path.exists():
            return None
            
        try:
            df = pd.read_csv(self.cache_path, index_col=0, parse_dates=True)
            logger.debug(f"Loaded cache with {len(df)} rows")
            return df
        except pd.errors.EmptyDataError:
            logger.warning("Cache file is empty")
            return None
        except pd.errors.ParserError as e:
            logger.error(f"Cache file parsing error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error loading cache: {e}")
            return None
    
    def save(self, df: pd.DataFrame) -> bool:
        """
        Save data to cache using atomic write.
        
        Uses a temp file + rename strategy to prevent corruption
        if the write is interrupted.
        
        Args:
            df: DataFrame to cache
            
        Returns:
            True if save succeeded, False otherwise.
        """
        temp_path = self.cache_path.with_suffix('.tmp')
        
        try:
            # Write to temp file first
            df.to_csv(temp_path)
            
            # Remove existing cache if present
            if self.cache_path.exists():
                os.remove(self.cache_path)
            
            # Atomic rename
            os.rename(temp_path, self.cache_path)
            
            logger.info(f"Cache saved: {len(df)} rows to {self.cache_path}")
            return True
            
        except PermissionError as e:
            logger.error(f"Permission denied writing cache: {e}")
            self._cleanup_temp(temp_path)
            return False
        except OSError as e:
            logger.error(f"OS error writing cache: {e}")
            self._cleanup_temp(temp_path)
            return False
        except Exception as e:
            logger.error(f"Unexpected error writing cache: {e}")
            self._cleanup_temp(temp_path)
            return False
    
    def _cleanup_temp(self, temp_path: Path) -> None:
        """Clean up temporary file if it exists."""
        try:
            if temp_path.exists():
                os.remove(temp_path)
        except Exception:
            pass
    
    def get_last_update_time(self) -> str:
        """
        Get human-readable last update timestamp.
        
        Returns:
            Formatted timestamp string or "N/A" if cache doesn't exist.
        """
        if not self.cache_path.exists():
            return "N/A"
            
        try:
            ts = os.path.getmtime(self.cache_path)
            return datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')
        except OSError:
            return "N/A"
    
    def get_last_data_date(self) -> Optional[datetime]:
        """
        Get the most recent date in the cached data.
        
        Returns:
            Last date in cache or None if cache is empty/invalid.
        """
        df = self.load()
        if df is not None and not df.empty:
            return df.index[-1].to_pydatetime()
        return None
    
    def invalidate(self) -> bool:
        """
        Force cache invalidation by deleting the cache file.
        
        Returns:
            True if cache was deleted or didn't exist, False on error.
        """
        if not self.cache_path.exists():
            return True
            
        try:
            os.remove(self.cache_path)
            logger.info("Cache invalidated")
            return True
        except Exception as e:
            logger.error(f"Error invalidating cache: {e}")
            return False
