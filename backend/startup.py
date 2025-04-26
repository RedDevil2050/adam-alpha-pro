import asyncio
from backend.core.orchestrator import SystemOrchestrator
from backend.utils.monitoring import SystemMonitor
from backend.config.logging_config import setup_logging
from backend.utils.cache_utils import redis_client
from loguru import logger

async def initialize_system():
    """Initialize all system components"""
    try:
        # Setup logging
        setup_logging()
        logger.info("Starting system initialization...")

        # Initialize core components
        system_monitor = SystemMonitor()
        orchestrator = SystemOrchestrator()
        
        # Verify Redis connection
        await redis_client.ping()
        logger.info("Redis connection verified")

        # Register components
        system_monitor.register_component("orchestrator")
        system_monitor.register_component("redis")
        system_monitor.register_component("api")

        # Warm up caches
        logger.info("Warming up system caches...")
        await orchestrator.warmup_caches()

        logger.info("System initialization complete")
        return orchestrator, system_monitor

    except Exception as e:
        logger.error(f"System initialization failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(initialize_system())
