
import json
import inspect
from functools import wraps
from loguru import logger
from backend.config.settings import settings

try:
    import redis.asyncio as redis
except ImportError:
    redis = None
    logger.warning("Redis module not installed. Caching disabled.")

redis_client = None

async def init_redis():
    global redis_client
    if redis is None:
        redis_client = None
        return
    try:
        redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
        await redis_client.ping()
        logger.info("Connected to Redis.")
    except Exception as e:
        redis_client = None
        logger.warning(f"Redis unavailable: {e}")

async def get_cache(key: str):
    if redis_client:
        try:
            result = await redis_client.get(key)
            if result:
                try:
                    return json.loads(result)
                except json.JSONDecodeError:
                    return result
        except Exception as e:
            logger.warning(f"Cache get error: {e}")
    return None

async def set_cache(key: str, value, ttl: int = settings.agent_cache_ttl):
    if redis_client:
        try:
            val = json.dumps(value) if isinstance(value, (dict, list)) else str(value)
            await redis_client.set(key, val, ex=ttl)
        except Exception as e:
            logger.warning(f"Cache set error: {e}")

def cache_data_provider(ttl: int = settings.agent_cache_ttl):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key_parts = [func.__name__] + [str(a) for a in args] + [f"{k}={v}" for k, v in kwargs.items()]
            cache_key = "data_provider:" + ":".join(key_parts)
            cached = await get_cache(cache_key)
            if cached is not None:
                logger.debug(f"Cache HIT {cache_key}")
                return cached
            result = await func(*args, **kwargs)
            if result is not None:
                await set_cache(cache_key, result, ttl)
            return result
        return wrapper
    return decorator
