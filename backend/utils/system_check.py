from typing import Dict
import aioredis
import psutil
from loguru import logger


class SystemCheck:
    @staticmethod
    async def verify_connections() -> Dict:
        results = {"redis": False, "disk": False, "memory": False, "cpu": False}

        try:
            # Redis check
            redis = aioredis.from_url("redis://localhost")
            await redis.ping()
            results["redis"] = True

            # System resources check
            results["disk"] = psutil.disk_usage("/").percent < 90
            results["memory"] = psutil.virtual_memory().percent < 90
            results["cpu"] = psutil.cpu_percent() < 80

            return {"status": all(results.values()), "components": results}
        except Exception as e:
            logger.error(f"System check failed: {e}")
            return {"status": False, "error": str(e), "components": results}
