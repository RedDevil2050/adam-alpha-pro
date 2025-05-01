import pytest
import pytest_asyncio # Import pytest_asyncio
from unittest.mock import AsyncMock, patch
import nltk # Import nltk

# Download vader_lexicon once per session
def pytest_configure(config):
    """Download NLTK data needed for tests."""
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
    """Globally mock redis_client for all tests."""
    # Use a context manager for patching
    with patch("backend.utils.cache_utils.get_redis_client", new_callable=AsyncMock) as mock_get_redis_client:
        # Configure the mock instance that get_redis_client will return
        mock_instance = AsyncMock()
        mock_instance.get.return_value = None  # Default behavior for get
        mock_instance.set.return_value = True  # Default behavior for set
        mock_instance.ping.return_value = True # Mock ping as well

        # Make the patched get_redis_client return the configured instance
        mock_get_redis_client.return_value = mock_instance

        # Yield the mock *instance* so it's correctly used by the code under test
        yield mock_instance # Yield the instance, not the mock function