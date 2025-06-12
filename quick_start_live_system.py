#!/usr/bin/env python3
"""
Quick Test and Start Script for Live Data System
===============================================

This script performs basic validation and starts the live data system.
"""

import asyncio
import sys
import subprocess
import time
from loguru import logger

async def test_basic_imports():
    """Test that all required modules can be imported"""
    logger.info("🔍 Testing basic imports...")
    
    try:
        from backend.services.continuous_data_service import continuous_data_service
        from backend.agents.stealth.background_manager import background_manager
        from backend.data_providers import ZerodhaProvider, AlphaVantageProvider
        logger.success("✅ All core modules imported successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Import failed: {e}")
        return False

async def test_service_creation():
    """Test that the continuous service can be created"""
    logger.info("🔍 Testing service creation...")
    
    try:
        from backend.services.continuous_data_service import continuous_data_service
        
        # Check if service has expected attributes
        assert hasattr(continuous_data_service, 'initialize')
        assert hasattr(continuous_data_service, 'get_session_status')
        assert hasattr(continuous_data_service, 'start_custom_session')
        
        logger.success("✅ Continuous data service created successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Service creation failed: {e}")
        return False

async def quick_initialization_test():
    """Quick test of service initialization"""
    logger.info("🔍 Testing quick initialization...")
    
    try:
        from backend.services.continuous_data_service import continuous_data_service
        
        # Try to get initial status (should work without full initialization)
        status = continuous_data_service.get_session_status()
        logger.info(f"📊 Initial status: {status}")
        
        logger.success("✅ Quick initialization test passed")
        return True
    except Exception as e:
        logger.error(f"❌ Quick initialization failed: {e}")
        return False

def start_backend_server():
    """Start the backend server"""
    logger.info("🚀 Starting backend server...")
    
    try:
        # Start uvicorn server
        cmd = [
            sys.executable, "-m", "uvicorn", 
            "app:app", 
            "--host", "0.0.0.0", 
            "--port", "8000", 
            "--reload"
        ]
        
        process = subprocess.Popen(
            cmd,
            cwd=".",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        logger.info("⏳ Server starting... (this may take a moment)")
        time.sleep(5)  # Give server time to start
        
        # Check if process is still running
        if process.poll() is None:
            logger.success("✅ Backend server started successfully!")
            logger.info("🌐 Server available at: http://localhost:8000")
            logger.info("📡 WebSocket endpoint: ws://localhost:8000/api/stealth/stream")
            logger.info("🔄 Continuous data status: http://localhost:8000/api/continuous/status")
            return process
        else:
            stdout, stderr = process.communicate()
            logger.error(f"❌ Server failed to start:")
            logger.error(f"STDOUT: {stdout}")
            logger.error(f"STDERR: {stderr}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Failed to start server: {e}")
        return None

async def main():
    """Main startup routine"""
    logger.info("🚀 Zion Live Data System - Quick Start")
    logger.info("=" * 50)
    
    # Step 1: Test imports
    if not await test_basic_imports():
        logger.error("❌ Basic imports failed. Check dependencies.")
        return False
    
    # Step 2: Test service creation
    if not await test_service_creation():
        logger.error("❌ Service creation failed. Check configuration.")
        return False
    
    # Step 3: Quick initialization test
    if not await quick_initialization_test():
        logger.error("❌ Quick initialization failed.")
        return False
    
    # Step 4: Start backend server
    logger.info("\n🚀 All tests passed! Starting backend server...")
    server_process = start_backend_server()
    
    if server_process:
        logger.success("🎉 Zion Live Data System is starting up!")
        logger.info("\n📋 Next Steps:")
        logger.info("   1. Wait for server to fully initialize (watch console output)")
        logger.info("   2. Frontend is available at: http://localhost:3000")
        logger.info("   3. Navigate to: http://localhost:3000/live-data")
        logger.info("   4. Test continuous data collection")
        logger.info("\n🛑 Press Ctrl+C to stop the server")
        
        try:
            # Keep the script running
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("\n🛑 Stopping server...")
            server_process.terminate()
            logger.info("👋 Server stopped")
    else:
        logger.error("❌ Failed to start backend server")
        return False

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n👋 Startup cancelled by user")
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        sys.exit(1)
