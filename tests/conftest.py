import pytest
import pytest_asyncio # Import pytest_asyncio
from unittest.mock import AsyncMock, patch, Mock
import nltk # Import nltk
import warnings # Add this line
import sys

# Download vader_lexicon once per session
def pytest_configure(config):
    """Download NLTK data needed for tests."""
    # Suppress the specific DeprecationWarning from pandas_ta related to pkg_resources
    warnings.filterwarnings(
        "ignore",
        category=DeprecationWarning,
        message=r"pkg_resources is deprecated as an API.*",
        module="pandas_ta"  # Filter for warnings originating from the pandas_ta module
    )
    
    # Also suppress RuntimeWarning for coroutine never awaited
    warnings.filterwarnings(
        "ignore",
        category=RuntimeWarning,
        message=r"coroutine '.*' was never awaited"
    )
    
    try:
        # Check if the resource exists to avoid repeated downloads
        nltk.data.find('sentiment/vader_lexicon.zip')
    except nltk.downloader.DownloadError:
        print("\nDownloading NLTK vader_lexicon...")
        nltk.download('vader_lexicon')
    except LookupError: # Handle cases where the path might be slightly different
        print("\nDownloading NLTK vader_lexicon (LookupError fallback)...")
        nltk.download('vader_lexicon')
    # Add other downloads here if needed, e.g., nltk.download('punkt')

@pytest_asyncio.fixture(scope="session", autouse=True) # Use pytest_asyncio.fixture
def mock_redis_client():
    """Globally mock redis_client for all tests with stateful behavior."""
    with patch("backend.utils.cache_utils.get_redis_client") as mock_get_redis_client:
        mock_instance = AsyncMock()
        actual_cache = {}  # Simple dict to simulate cache storage

        async def mock_get(key):
            # logger.debug(f"Mock Redis GET: key={key}, value={actual_cache.get(key, None)}")
            return actual_cache.get(key, None)

        async def mock_set(key, value, ex=None): # ex is for expiry
            # logger.debug(f"Mock Redis SET: key={key}, value={value}, ex={ex}")
            actual_cache[key] = value
            return True

        async def mock_delete(key):
            # logger.debug(f"Mock Redis DELETE: key={key}")
            if key in actual_cache:
                del actual_cache[key]
                return 1
            return 0

        mock_instance.get = AsyncMock(side_effect=mock_get)
        mock_instance.set = AsyncMock(side_effect=mock_set)
        mock_instance.delete = AsyncMock(side_effect=mock_delete)
        mock_instance.ping = AsyncMock(return_value=True) # Mock ping as well

        # Make get_redis_client return the client directly instead of being a coroutine
        # This way when the function is called without await, it won't cause warnings
        mock_get_redis_client.return_value = mock_instance
        yield mock_instance
        actual_cache.clear() # Clear cache after session