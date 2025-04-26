import asyncio
from backend.core.orchestrator import SystemOrchestrator
from backend.utils.system_monitor import SystemMonitor
from backend.utils.cache_utils import redis_client
from backend.config.settings import settings
from backend.config.logging_config import setup_logging
from loguru import logger

async def initialize_system():
    """Initialize all system components with market checks"""
    try:
        # Setup logging
        setup_logging()
        logger.info("Starting system initialization...")

        # Initialize Redis
        await verify_redis_connection()

        # Initialize core components
        system_monitor = SystemMonitor()
        orchestrator = SystemOrchestrator()
        
        # Register and verify components
        await register_components(system_monitor)
        
        # Verify system ready
        readiness = system_monitor.is_ready()
        if not readiness["ready"]:
            logger.warning(f"System not fully ready: {readiness}")
            if not readiness["components"].get("redis"):
                raise RuntimeError("Redis component not healthy")
        else:
            logger.info("System initialization complete and ready")
            
        return orchestrator, system_monitor

    except Exception as e:
        logger.error(f"System initialization failed: {e}")
        raise

async def verify_redis_connection():
    """Verify Redis connection"""
    try:
        await redis_client.ping()
        logger.info("Redis connection verified")
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        raise

async def register_components(monitor: SystemMonitor):
    """Register and verify all components"""
    components = ["orchestrator", "redis", "api", "cache"]
    for component in components:
        monitor.register_component(component)
    logger.info(f"Registered {len(components)} components")

if __name__ == "__main__":
    asyncio.run(initialize_system())
