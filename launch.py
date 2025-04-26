import asyncio
import uvicorn
from backend.startup import initialize_system
from backend.api.main import app
from loguru import logger
import signal

async def verify_launch_readiness():
    """Pre-launch verification"""
    orchestrator, monitor = await initialize_system()
    
    # Verify all critical systems
    market_status = monitor.check_market_readiness()
    system_ready = monitor.is_ready()
    health = monitor.check_system_health()
    
    if not all([
        market_status["market_ready"],
        system_ready["ready"],
        health["status"] == "healthy",
        market_status["resources_available"]
    ]):
        logger.error("Launch verification failed")
        logger.error(f"Market status: {market_status}")
        logger.error(f"System ready: {system_ready}")
        logger.error(f"Health: {health}")
        return None, None
        
    logger.info("✅ Launch verification complete - all systems go")
    return orchestrator, monitor

async def verify_end_to_end():
    """Verify complete data flow and analysis pipeline"""
    try:
        test_symbol = "AAPL"  # Test with a reliable symbol
        
        # Test market data flow
        logger.info("Testing market data pipeline...")
        data_result = await app.state.orchestrator.get_market_data(test_symbol)
        if not data_result:
            raise RuntimeError("Market data pipeline failed")
            
        # Test analysis pipeline
        logger.info("Testing analysis pipeline...")
        analysis_result = await app.state.orchestrator.analyze_symbol(test_symbol)
        if not analysis_result or "error" in analysis_result:
            raise RuntimeError(f"Analysis pipeline failed: {analysis_result.get('error', 'Unknown error')}")
            
        # Verify verdict generation
        if "verdict" not in analysis_result:
            raise RuntimeError("Verdict generation failed")
            
        logger.info("✅ End-to-end pipeline verification successful")
        return True
    except Exception as e:
        logger.error(f"End-to-end verification failed: {e}")
        return False

async def launch():
    """Main launch sequence"""
    try:
        # Pre-launch verification
        orchestrator, monitor = await verify_launch_readiness()
        if not orchestrator or not monitor:
            raise RuntimeError("Launch verification failed")
            
        app.state.orchestrator = orchestrator
        app.state.monitor = monitor

        # End-to-end verification
        if not await verify_end_to_end():
            raise RuntimeError("End-to-end verification failed")

        # Launch configuration
        config = uvicorn.Config(
            app=app,
            host="0.0.0.0",
            port=8000,
            workers=4,
            log_level="info"
        )
        
        logger.info("🚀 Launching Zion Market Analysis System")
        server = uvicorn.Server(config)
        
        # Setup graceful shutdown
        def handle_shutdown(signum, frame):
            logger.info("Initiating graceful shutdown...")
            
        signal.signal(signal.SIGINT, handle_shutdown)
        signal.signal(signal.SIGTERM, handle_shutdown)
        
        await server.serve()
        
    except Exception as e:
        logger.error(f"Launch failed: {e}")
        raise

if __name__ == "__main__":
    logger.info("Starting launch sequence...")
    asyncio.run(launch())
