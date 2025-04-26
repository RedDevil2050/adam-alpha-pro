from redis.asyncio import Redis
from backend.config.settings import settings
from loguru import logger

try:
    redis_client = Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        decode_responses=True
    )
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
