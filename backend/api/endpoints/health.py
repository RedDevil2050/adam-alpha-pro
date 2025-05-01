from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from backend.db.session import get_db
import redis.asyncio as redis
from backend.utils.cache_utils import get_redis_client
import time
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])

@router.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db)
):
    """
    Performs health checks on critical system components (DB, Cache).
    """
    start_time = time.monotonic()
    db_ok = False
    redis_ok = False
    db_latency = None
    redis_latency = None

    # Check Database Connection
    db_check_start = time.monotonic()
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
        logger.debug("Database connection successful.")
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
    db_latency = (time.monotonic() - db_check_start) * 1000  # milliseconds

    # Check Redis Connection
    redis_check_start = time.monotonic()
    try:
        redis_client = await get_redis_client()
        # Try to set and get a test value
        test_key = "health_check_test"
        test_value = "ok"
        redis_client.set(test_key, test_value)
        result = redis_client.get(test_key)
        redis_client.delete(test_key)
        redis_ok = result == test_value
        logger.debug("Redis connection successful.")
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
    redis_latency = (time.monotonic() - redis_check_start) * 1000  # milliseconds

    total_latency = (time.monotonic() - start_time) * 1000

    status_code = 200 if db_ok and redis_ok else 503  # Service Unavailable

    response = {
        "status": "healthy" if db_ok and redis_ok else "unhealthy",
        "services": {
            "database": {
                "status": "healthy" if db_ok else "unhealthy",
                "latency_ms": f"{db_latency:.2f}"
            },
            "redis": {
                "status": "healthy" if redis_ok else "unhealthy",
                "latency_ms": f"{redis_latency:.2f}"
            }
        },
        "total_latency_ms": f"{total_latency:.2f}"
    }

    if status_code != 200:
        raise HTTPException(status_code=status_code, detail=response)

    return response