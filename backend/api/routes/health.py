from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
import psutil
import redis
import asyncpg
from backend.config.settings import get_settings
from backend.utils.data_provider import fetch_market_data

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
        "components": {}
    }
    
    # Check Redis
    try:
        redis_client = redis.from_url(settings.REDIS_URL)
        redis_client.ping()
        details["components"]["redis"] = "healthy"
    except Exception as e:
        details["components"]["redis"] = f"unhealthy: {str(e)}"

    # Check Database
    try:
        conn = await asyncpg.connect(
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_NAME,
            host=settings.DB_HOST
        )
        await conn.execute('SELECT 1')
        await conn.close()
        details["components"]["database"] = "healthy"
    except Exception as e:
        details["components"]["database"] = f"unhealthy: {str(e)}"

    # Check Market Data
    try:
        market_data = await fetch_market_data()
        if market_data:
            details["components"]["market_data"] = "healthy"
        else:
            details["components"]["market_data"] = "unhealthy: no data received"
    except Exception as e:
        details["components"]["market_data"] = f"unhealthy: {str(e)}"

    # Determine overall status
    is_healthy = all(
        v == "healthy" for v in details["components"].values()
    ) and details["system"]["cpu_usage"] < 80 and details["system"]["memory_usage"] < 85

    if not is_healthy:
        raise HTTPException(
            status_code=503,
            detail="Service unhealthy",
            headers={"Retry-After": "30"}
        )

    return HealthResponse(
        status="healthy" if is_healthy else "unhealthy",
        details=details
    )