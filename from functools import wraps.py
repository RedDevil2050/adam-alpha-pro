from functools import wraps
import json
from redis import Redis
from ..config.settings import get_settings
from ..monitoring.metrics import cache_hits, cache_misses

settings = get_settings()
redis_client = Redis.from_url(settings.REDIS_URL)

def cache_data(ttl: int = 300):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{args}:{kwargs}"
            
            # Try getting from cache
            cached = await redis_client.get(cache_key)
            if cached:
                cache_hits.inc()
                return json.loads(cached)
            
            # Get fresh data
            cache_misses.inc()
            result = await func(*args, **kwargs)
            
            # Cache the result
            await redis_client.set(
                cache_key,
                json.dumps(result),
                ex=ttl
            )
            return result
        return wrapper
    return decorator
