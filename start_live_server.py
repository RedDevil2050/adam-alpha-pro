#!/usr/bin/env python3
"""
Zion Live Data Server Startup Script
===================================

Starts the complete live data collection system with:
- Continuous data collection service
- WebSocket streaming
- Health monitoring
- Auto-recovery mechanisms
"""

import asyncio
import uvicorn
import argparse
from loguru import logger
from backend.services.continuous_data_service import continuous_data_service

async def pre_startup_checks():
    """Perform pre-startup system checks"""
    logger.info("🔍 Performing pre-startup checks...")
    
    try:
        # Check if required dependencies are available
        import redis
        import httpx
        import yfinance
        logger.info("✅ Required dependencies available")
        
        # Test Redis connection
        try:
            from backend.utils.cache_utils import get_redis_client
            redis_client = get_redis_client()
            if redis_client:
                redis_client.ping()
                logger.info("✅ Redis connection successful")
            else:
                logger.warning("⚠️ Redis not available - caching will be limited")
        except Exception as e:
            logger.warning(f"⚠️ Redis connection failed: {e}")
        
        logger.success("✅ Pre-startup checks completed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Pre-startup checks failed: {e}")
        return False

def setup_logging():
    """Configure enhanced logging"""
    logger.remove()  # Remove default handler
    
    # Console logging with colors
    logger.add(
        lambda msg: print(msg, end=""),
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO"
    )
    
    # File logging
    logger.add(
        "logs/zion_live_data_{time:YYYY-MM-DD}.log",
        rotation="1 day",
        retention="7 days",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
    )

async def main():
    """Main startup routine"""
    parser = argparse.ArgumentParser(description="Zion Live Data Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--dev", action="store_true", help="Development mode with auto-reload")
    parser.add_argument("--log-level", default="info", choices=["debug", "info", "warning", "error"])
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging()
    
    logger.info("🚀 Starting Zion Live Data Server...")
    logger.info(f"   Host: {args.host}")
    logger.info(f"   Port: {args.port}")
    logger.info(f"   Development mode: {args.dev}")
    
    # Pre-startup checks
    if not await pre_startup_checks():
        logger.error("❌ Pre-startup checks failed. Exiting.")
        return
    
    # Configure uvicorn
    config = uvicorn.Config(
        "app:app",
        host=args.host,
        port=args.port,
        log_level=args.log_level,
        reload=args.dev,
        access_log=True
    )
    
    server = uvicorn.Server(config)
    
    logger.success("✅ Zion Live Data Server starting...")
    logger.info("🌐 Server will be available at:")
    logger.info(f"   - Local: http://localhost:{args.port}")
    logger.info(f"   - Network: http://{args.host}:{args.port}")
    logger.info(f"📡 WebSocket endpoint: ws://localhost:{args.port}/api/stealth/stream")
    logger.info(f"📊 Health check: http://localhost:{args.port}/api/health")
    logger.info(f"🔄 Continuous data status: http://localhost:{args.port}/api/continuous/status")
    
    try:
        await server.serve()
    except KeyboardInterrupt:
        logger.info("🛑 Received shutdown signal")
    except Exception as e:
        logger.error(f"❌ Server error: {e}")
    finally:
        logger.info("👋 Zion Live Data Server stopped")

if __name__ == "__main__":
    asyncio.run(main())
