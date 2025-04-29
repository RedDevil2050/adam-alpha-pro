import asyncio
# Make sure SystemOrchestrator is imported
from backend.core.orchestrator import SystemOrchestrator
from backend.utils.system_monitor import SystemMonitor
# Assuming redis_client is the cache client needed by Orchestrator
from backend.utils.cache_utils import redis_client
from backend.config.settings import settings
from backend.config.logging_config import setup_logging
from loguru import logger
# Import necessary API components if needed for initialization
# from backend.api.main import initialize_api # Example

async def initialize_system():
    """Initialize all system components with market checks"""
    system_monitor = None
    orchestrator = None
    try:
        # Setup logging
        setup_logging()
        logger.info("Starting system initialization...")

        # Initialize core components first
        system_monitor = SystemMonitor()
        # Instantiate Orchestrator, passing dependencies
        orchestrator = SystemOrchestrator(cache_client=redis_client)

        # Register components first, setting them to initializing
        await register_components(system_monitor) # Registers orchestrator, redis, api, cache

        # Initialize and verify Redis, then update status
        await verify_redis_connection(system_monitor) # Updates 'redis' status

        # Initialize Orchestrator, updating its status
        await orchestrator.initialize(system_monitor) # Updates 'orchestrator' status

        # TODO: Initialize API component and update its status
        # Example: await initialize_api(system_monitor) # This would update 'api' status
        # For now, let's assume API starts elsewhere or doesn't need async init here
        # We'll manually mark it as healthy for now, assuming it's ready if code reaches here
        # Replace this with actual API initialization if required
        system_monitor.update_component_status("api", "healthy")
        logger.info("API component assumed healthy (replace with actual init if needed)")

        # Mark 'cache' component as healthy (tied to redis verification)
        # If redis failed, the exception would have been raised already
        if system_monitor.components.get("redis", {}).get("status") == "healthy":
             system_monitor.update_component_status("cache", "healthy")
             logger.info("Cache component marked healthy (linked to Redis)")
        else:
             # This case might not be reached if verify_redis_connection raises on failure
             system_monitor.update_component_status("cache", "failed")
             logger.warning("Cache component marked failed (linked to Redis)")


        # Verify system ready
        readiness = system_monitor.is_ready()
        if not readiness["ready"]:
            logger.warning(f"System not fully ready after initialization: {readiness}")
            # Optional: Add more specific checks or wait logic here
        else:
            logger.info("System initialization complete and ready")

        # Return initialized components
        return orchestrator, system_monitor

    except Exception as e:
        logger.error(f"System initialization failed: {e}")
        if system_monitor: # Update component statuses to failed if monitor exists
            # Mark all components that are still initializing or not healthy as failed
            for name, details in system_monitor.components.items():
                if details["status"] != "healthy":
                    system_monitor.update_component_status(name, "failed")
        raise


async def verify_redis_connection(monitor: SystemMonitor): # Accept monitor instance
    """Verify Redis connection and update status"""
    component_name = "redis"
    try:
        await redis_client.ping()
        logger.info("Redis connection verified")
        monitor.update_component_status(component_name, "healthy") # Update status to healthy
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        monitor.update_component_status(component_name, "failed") # Update status to failed
        raise


async def register_components(monitor: SystemMonitor):
    """Register all components with initial status"""
    # Log the type of monitor object for debugging the previous error
    logger.debug(f"Registering components with monitor object: {type(monitor)}")
    components = ["orchestrator", "redis", "api", "cache"]
    for component in components:
        monitor.register_component(component) # Status defaults to 'initializing'
    logger.info(f"Registered {len(components)} components")


if __name__ == "__main__":
    asyncio.run(initialize_system())
