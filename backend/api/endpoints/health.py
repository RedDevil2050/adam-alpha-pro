from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database.db import get_db # Use absolute import from project root
import redis.asyncio as redis
from backend.utils.cache_utils import get_redis_client # Use absolute import from project root
import time
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/health", tags=["system"])
async def health_check(
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client)
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
        # Execute a simple query
        await db.execute("SELECT 1")
        db_ok = True
        logger.debug("Database connection successful.")
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
    db_latency = (time.monotonic() - db_check_start) * 1000 # milliseconds

    # Check Redis Connection
    redis_check_start = time.monotonic()
    try:
        await redis_client.ping()
        redis_ok = True
        logger.debug("Redis connection successful.")
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
    redis_latency = (time.monotonic() - redis_check_start) * 1000 # milliseconds

    total_latency = (time.monotonic() - start_time) * 1000

    status_code = 200 if db_ok and redis_ok else 503 # Service Unavailable

    response = {
        "status": "ok" if db_ok and redis_ok else "error",
        "details": {
            "database": {"status": "ok" if db_ok else "error", "latency_ms": f"{db_latency:.2f}"},
            "cache": {"status": "ok" if redis_ok else "error", "latency_ms": f"{redis_latency:.2f}"}
        },
        "total_latency_ms": f"{total_latency:.2f}"
    }

    if status_code != 200:
        raise HTTPException(status_code=status_code, detail=response)

    return response