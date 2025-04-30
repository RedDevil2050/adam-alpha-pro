from unittest.mock import AsyncMock

# Replace the Redis client with a mock for testing purposes
_redis_client = AsyncMock()
_redis_client.get.return_value = None
_redis_client.ping.return_value = True

# Define the function that the rest of the code expects to import
def get_redis_client():
    """Returns the Redis client instance (mocked for testing)."""
    # In a real application, this would initialize and return a real Redis client.
    # For testing purposes, we return the predefined mock.
    return _redis_client
