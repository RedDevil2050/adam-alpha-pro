from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
import redis
import psutil
from backend.config.settings import get_settings
from backend.utils.cache_utils import get_redis_client

router = APIRouter()

class HealthResponse(BaseModel):
    status: str
    details: Dict[str, Any]

@router.get("/health", response_model=HealthResponse)
async def health_check():
    settings = get_settings()
    details = {
        "system": {
            "cpu_usage": psutil.cpu_percent(),
            "memory_usage": psutil.virtual_memory().percent
        },
        "components": {},
        "flags": {
            "is_staging": True,
            "market_hours": "16:00-08:30 IST"
        }
    }
    
    is_healthy = True
    
    # Check Redis
    try:
        redis_client = get_redis_client()
        redis_client.ping()
        details["components"]["redis"] = "healthy"
    except Exception as e:
        details["components"]["redis"] = f"unhealthy: {str(e)}"
        is_healthy = False

    # System checks
    if details["system"]["cpu_usage"] >= 80:
        is_healthy = False
    if details["system"]["memory_usage"] >= 85:
        is_healthy = False

    if not is_healthy:
        raise HTTPException(
            status_code=503,
            detail="Service unhealthy",
            headers={"Retry-After": "30"}
        )

    return HealthResponse(
        status="healthy",
        details=details
    )