import pytest
from unittest.mock import AsyncMock, patch

@pytest.fixture(scope="session", autouse=True)
def mock_redis_client():
    """Globally mock redis_client for all tests."""
    with patch("backend.utils.cache_utils.redis_client", new_callable=AsyncMock) as mock_redis:
        mock_redis.get.return_value = None  # Default behavior for get
        mock_redis.set.return_value = True  # Default behavior for set
        yield mock_redis