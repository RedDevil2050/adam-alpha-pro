import time
from typing import Dict, Any
import psutil
import logging  # Import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.session import get_db
from ...config.settings import get_settings

# Get logger instance
logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", summary="Health Check Endpoint")
async def health_check(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Health check endpoint for the application.
    Returns system health metrics and connection statuses.
    Used by container orchestration and monitoring systems.
    """
    start_time = time.time()
    health_data = {
        "status": "healthy",
        "timestamp": time.time(),
        "uptime": time.time() - psutil.boot_time(),
        "version": "1.0.0",  # Should be pulled from a version file or env var
        "services": {}
    }
    
    # Check database connection
    db_start_time = time.time()
    try:
        logger.info("Health check: Attempting database connection check...")
        # Simple database query to verify connection
        result = await db.execute("SELECT 1")
        await result.fetchone()
        db_latency = time.time() - db_start_time
        health_data["services"]["database"] = {
            "status": "up",
            "latency_ms": round(db_latency * 1000, 2)
        }
        logger.info(f"Health check: Database connection successful (Latency: {db_latency*1000:.2f}ms)")
    except Exception as e:
        db_latency = time.time() - db_start_time
        logger.error(f"Health check: Database connection failed after {db_latency*1000:.2f}ms: {e}", exc_info=True) # Log exception info
        health_data["status"] = "degraded"
        health_data["services"]["database"] = {
            "status": "down",
            "error": str(e),
            "latency_ms": round(db_latency * 1000, 2) # Add latency even on failure
        }
    
    # Check Redis connection if used
    redis_start_time = time.time()
    try:
        from ...utils.cache_utils import redis_client
        logger.info("Health check: Attempting Redis connection check...")
        if await redis_client.ping():
            redis_latency = time.time() - redis_start_time
            health_data["services"]["redis"] = {
                "status": "up",
                "latency_ms": round(redis_latency * 1000, 2)
            }
            logger.info(f"Health check: Redis connection successful (Latency: {redis_latency*1000:.2f}ms)")
        else:
            # This case might not be hit if ping() raises an exception on failure, but included for completeness
            redis_latency = time.time() - redis_start_time
            logger.error(f"Health check: Redis ping failed after {redis_latency*1000:.2f}ms (returned False)")
            raise Exception("Redis ping failed")
    except ImportError:
        logger.warning("Health check: Redis client not found (cache_utils import failed). Skipping Redis check.")
        # Optionally mark redis as 'not_configured' or similar if needed
        pass # If redis is optional, don't mark status as degraded
    except Exception as e:
        redis_latency = time.time() - redis_start_time
        logger.error(f"Health check: Redis connection failed after {redis_latency*1000:.2f}ms: {e}", exc_info=True) # Log exception info
        health_data["status"] = "degraded"
        health_data["services"]["redis"] = {
            "status": "down",
            "error": str(e),
            "latency_ms": round(redis_latency * 1000, 2) # Add latency even on failure
        }
    
    # Add system resource metrics
    health_data["system"] = {
        "cpu_usage": psutil.cpu_percent(interval=None),
        "memory_usage": psutil.virtual_memory().percent,
        "disk_usage": psutil.disk_usage('/').percent
    }
    
    # Return 503 Service Unavailable if critical services are down
    if health_data["status"] != "healthy":
        # Raise 503 if either DB or Redis is down (and Redis is configured/expected)
        db_down = health_data["services"].get("database", {}).get("status") == "down"
        # Check if redis service exists in health_data before checking its status
        redis_down = health_data["services"].get("redis", {}).get("status") == "down"

        if db_down or redis_down:
            logger.warning(f"Health check reporting unhealthy: DB Down={db_down}, Redis Down={redis_down}. Raising 503.")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=health_data
            )
    
    # Calculate total response time
    health_data["response_time_ms"] = round((time.time() - start_time) * 1000, 2)
    
    return health_data


@router.get("/health/live", summary="Liveness Probe")
def liveness_probe() -> Dict[str, str]:
    """
    Lightweight liveness probe for Kubernetes/container orchestrators.
    Only checks if the application is running, not dependent services.
    """
    return {"status": "alive"}


@router.get("/health/ready", summary="Readiness Probe")
async def readiness_probe(db: AsyncSession = Depends(get_db)) -> Dict[str, str]:
    """
    Readiness probe for Kubernetes/container orchestrators.
    Checks if the application is ready to receive traffic.
    Verifies database connectivity.
    """
    try:
        result = await db.execute("SELECT 1")
        await result.fetchone()
        return {"status": "ready"}
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "not ready", "reason": "database connection failed"}
        )
