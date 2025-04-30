from unittest.mock import AsyncMock

# Replace the Redis client with a mock for testing purposes
_redis_client = AsyncMock()
_redis_client.get.return_value = None
_redis_client.ping.return_value = True
