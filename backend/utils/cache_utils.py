import redis
import os
from loguru import logger
from typing import Optional
import time
from functools import wraps

_redis_client: Optional[redis.Redis] = None

def get_redis_client() -> redis.Redis:
    """Get Redis client instance with connection pooling and retries"""
    global _redis_client
    if _redis_client is None:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        for attempt in range(3):  # Try 3 times
            try:
                _redis_client = redis.from_url(
                    redis_url,
                    socket_timeout=5,
                    socket_connect_timeout=5,
                    retry_on_timeout=True,
                    decode_responses=True
                )
                # Test connection
                _redis_client.ping()
                logger.info(f"Successfully connected to Redis at {redis_url}")
                break
            except redis.ConnectionError as e:
                if attempt == 2:  # Last attempt
                    logger.error(f"Failed to connect to Redis at {redis_url} after 3 attempts: {e}")
                    raise
                logger.warning(f"Redis connection attempt {attempt + 1} failed, retrying...")
                time.sleep(1)  # Wait before retry
    return _redis_client

def cache_decorator(ttl: int = 3600):
    """Decorator for caching function results in Redis"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                redis_client = get_redis_client()
                # Create a cache key from function name and arguments
                key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
                # Try to get cached result
                result = redis_client.get(key)
                if result:
                    return result
                # If no cached result, execute function
                result = await func(*args, **kwargs)
                # Cache the result
                redis_client.setex(key, ttl, str(result))
                return result
            except redis.RedisError as e:
                logger.warning(f"Redis error in cache decorator: {e}")
                # If Redis fails, just execute the function
                return await func(*args, **kwargs)
        return wrapper
    return decorator
