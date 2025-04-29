import time
from typing import Dict, Any
import psutil

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.session import get_db
from ...config.settings import get_settings

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
    try:
        # Simple database query to verify connection
        result = await db.execute("SELECT 1")
        await result.fetchone()
        health_data["services"]["database"] = {
            "status": "up",
            "latency_ms": round((time.time() - start_time) * 1000, 2)
        }
    except Exception as e:
        health_data["status"] = "degraded"
        health_data["services"]["database"] = {
            "status": "down",
            "error": str(e)
        }
    
    # Check Redis connection if used
    try:
        from ...utils.cache_utils import redis_client
        redis_start_time = time.time()
        if await redis_client.ping():
            redis_latency = time.time() - redis_start_time
            health_data["services"]["redis"] = {
                "status": "up",
                "latency_ms": round(redis_latency * 1000, 2)
            }
        else:
            raise Exception("Redis ping failed")
    except Exception as e:
        health_data["status"] = "degraded"
        health_data["services"]["redis"] = {
            "status": "down",
            "error": str(e)
        }
    
    # Add system resource metrics
    health_data["system"] = {
        "cpu_usage": psutil.cpu_percent(interval=None),
        "memory_usage": psutil.virtual_memory().percent,
        "disk_usage": psutil.disk_usage('/').percent
    }
    
    # Return 503 Service Unavailable if critical services are down
    if health_data["status"] != "healthy":
        # Raise 503 if either DB or Redis is down
        if (health_data["services"].get("database", {}).get("status") == "down" or
            health_data["services"].get("redis", {}).get("status") == "down"):
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
