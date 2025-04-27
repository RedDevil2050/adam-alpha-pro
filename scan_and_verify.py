import os
import asyncio
from pathlib import Path
from loguru import logger
from backend.utils.cache_utils import redis_client
from backend.startup import initialize_system

async def check_redis():
    try:
        pong = await redis_client.ping()
        return pong
    except Exception as e:
        logger.error(f"Redis check failed: {e}")
        return False

async def check_api():
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/health")
            return response.status_code == 200
    except Exception as e:
        logger.error(f"API check failed: {e}")
        return False

def check_config_files():
    required_files = [
        "deploy/production-config.env",
        "requirements.txt",
        "docker-compose.yml"
    ]
    missing_files = [f for f in required_files if not Path(f).exists()]
    if missing_files:
        logger.error(f"Missing configuration files: {missing_files}")
        return False
    return True

async def scan_and_verify():
    logger.info("🔍 Scanning system for readiness...")

    # Check Redis
    redis_ready = await check_redis()
    logger.info(f"Redis Ready: {redis_ready}")

    # Check API
    api_ready = await check_api()
    logger.info(f"API Ready: {api_ready}")

    # Check configuration files
    config_ready = check_config_files()
    logger.info(f"Configuration Files Ready: {config_ready}")

    # Initialize system
    orchestrator, monitor = await initialize_system()
    system_ready = monitor.is_ready() if monitor else {"ready": False}
    logger.info(f"System Ready: {system_ready['ready']}")

    # Final readiness check
    if redis_ready and api_ready and config_ready and system_ready["ready"]:
        logger.info("✅ System is ready for launch!")
    else:
        logger.error("❌ System is not ready for launch. Please address the issues above.")

if __name__ == "__main__":
    asyncio.run(scan_and_verify())
