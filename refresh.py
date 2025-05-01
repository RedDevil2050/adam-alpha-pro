import asyncio
import sys
from pathlib import Path
from loguru import logger

sys.path.append(str(Path(__file__).parent))

from backend.startup import initialize_system
from backend.utils.cache_utils import get_redis_client
from backend.utils.system_monitor import SystemMonitor

async def refresh_system():
    logger.info("Starting system refresh...")
    
    try:
        # Clear Redis cache
        redis_client = await get_redis_client()
        await redis_client.flushall()
        logger.info("Cache cleared")
        
        # Stop existing monitors
        monitor = SystemMonitor()
        await monitor.stop_all()
        logger.info("Stopped system monitors")
        
        # Reinitialize system
        orchestrator, monitor = await initialize_system()
        if not orchestrator or not monitor:
            logger.error("System reinitialization failed")
            return False
            
        # Verify system health
        health = monitor.check_system_health()
        if health["status"] != "healthy":
            logger.error(f"System unhealthy after refresh: {health}")
            return False
            
        logger.info("System refresh completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Refresh failed: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(refresh_system())
