from redis.asyncio import Redis
from backend.config.settings import settings
from loguru import logger
import os

try:
    # Parse the Redis URL to connect
    redis_url = getattr(settings, 'REDIS_URL', 'redis://localhost:6379/0')
    redis_client = Redis.from_url(url=redis_url, decode_responses=True)
    # Log the source of the Redis URL
    if 'REDIS_URL' in os.environ:
        logger.info("Using Redis URL from environment variable: %s", redis_url)
    else:
        logger.info("Using default Redis URL: %s", redis_url)
except Exception as e:
    logger.error(f"Failed to initialize Redis client: {e}")
    redis_client = None


def cache_data_provider(ttl=3600):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            if not redis_client:
                return await func(*args, **kwargs)
            # Rest of caching logic
            return await func(*args, **kwargs)

        return wrapper

    return decorator
