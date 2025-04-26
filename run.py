import asyncio
import uvicorn
from backend.startup import initialize_system
from backend.api.main import app
from loguru import logger

async def main():
    try:
        # Initialize core system
        orchestrator, monitor = await initialize_system()
        
        # Add system components to app state
        app.state.orchestrator = orchestrator
        app.state.monitor = monitor
        
        # Start uvicorn server
        config = uvicorn.Config(
            app=app,
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()
        
    except Exception as e:
        logger.error(f"System launch failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
