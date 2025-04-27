from fastapi import Request, HTTPException
from redis.asyncio import Redis
from ..config.settings import get_settings

settings = get_settings()

class RateLimiter:
    def __init__(self, redis_url: str = settings.redis.REDIS_URL, limit: int = 100, window: int = 60):
        self.redis = Redis.from_url(redis_url)
        self.limit = limit
        self.window = window

    async def check_rate_limit(self, key: str):
        redis_key = f"rate_limit:{key}"
        count = await self.redis.incr(redis_key)
        if count == 1:
            await self.redis.expire(redis_key, self.window)
        if count > self.limit:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Try again later."
            )
