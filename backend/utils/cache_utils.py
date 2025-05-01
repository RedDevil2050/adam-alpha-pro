from unittest.mock import AsyncMock

# Create an AsyncMock instance for the Redis client
_redis_client = AsyncMock()

# Configure the mock methods with AsyncMock
_redis_client.get = AsyncMock(return_value=None)
_redis_client.set = AsyncMock(return_value=True)
_redis_client.ping = AsyncMock(return_value=True)

async def get_redis_client():
    """Returns the Redis client instance (mocked for testing)."""
    # In a real application, this would initialize and return a real Redis client.
    # For testing purposes, we return the predefined mock.
    return _redis_client
