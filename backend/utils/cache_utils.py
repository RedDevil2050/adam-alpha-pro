import aioredis
from backend.config.settings import settings

redis_client = aioredis.from_url(
    f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}",
    encoding="utf-8",
    decode_responses=True
)
