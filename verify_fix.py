import sys
from unittest.mock import MagicMock
sys.modules['streamlit'] = MagicMock()
sys.modules['seaborn'] = MagicMock()

try:
    from app import DataManager
except ImportError:
    import os
    sys.path.append(os.getcwd())
    from app import DataManager

import pandas as pd

def test_fix():
    print("Initializing DataManager...")
    dm = DataManager()
    
    if hasattr(dm, '_is_cache_valid'):
        print("SUCCESS: _is_cache_valid method found.")
    else:
        print("FAILURE: _is_cache_valid method missing.")
        sys.exit(1)

    if hasattr(dm, '_fetch_fred_series'):
         print("SUCCESS: _fetch_fred_series method found.")
    else:
         print("FAILURE: _fetch_fred_series method missing.")
         sys.exit(1)

    if hasattr(dm, '_download_from_web'):
         print("SUCCESS: _download_from_web method found.")
    else:
         print("FAILURE: _download_from_web method missing.")
         sys.exit(1)

    print("Verification passed.")

if __name__ == "__main__":
    test_fix()
