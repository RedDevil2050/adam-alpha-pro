#!/usr/bin/env python3
"""
Test Continuous Live Data Collection System
==========================================

Comprehensive test suite for the continuous data collection service
including API failover, stealth agent backup, and real-time streaming.
"""

import asyncio
import time
import json
import httpx
import websockets
from loguru import logger
from backend.services.continuous_data_service import continuous_data_service

async def test_continuous_service_initialization():
    """Test the continuous service initialization"""
    logger.info("🧪 Testing Continuous Service Initialization")
    logger.info("=" * 60)
    
    try:
        # Initialize the service
        await continuous_data_service.initialize()
        
        # Check if default session started
        status = continuous_data_service.get_session_status()
        logger.info(f"📊 Service Status: {json.dumps(status, indent=2)}")
        
        if status.get("active_sessions", 0) > 0:
            logger.success("✅ Default continuous session started successfully")
            return True
        else:
            logger.error("❌ No active sessions found")
            return False
            
    except Exception as e:
        logger.error(f"❌ Service initialization failed: {e}")
        return False

async def test_api_providers():
    """Test API data providers directly"""
    logger.info("\n🧪 Testing API Data Providers")
    logger.info("=" * 60)
    
    test_symbol = "RELIANCE"
    providers = continuous_data_service.api_providers
    
    for provider_name, provider in providers.items():
        try:
            logger.info(f"🔍 Testing {provider_name}...")
            data = await provider.get_live_price(test_symbol)
            
            if data and not data.get("error"):
                logger.success(f"✅ {provider_name}: {data}")
            else:
                logger.warning(f"⚠️ {provider_name}: {data}")
                
        except Exception as e:
            logger.error(f"❌ {provider_name} failed: {e}")

async def test_stealth_agents():
    """Test stealth agents directly"""
    logger.info("\n🧪 Testing Stealth Agents")
    logger.info("=" * 60)
    
    test_symbol = "TCS"
    agents = continuous_data_service.stealth_agents
    
    for agent_name, agent in agents.items():
        try:
            logger.info(f"🔍 Testing {agent_name}...")
            data = await agent.execute(test_symbol)
            
            if data and not data.get("error"):
                logger.success(f"✅ {agent_name}: Price = {data.get('price', 'N/A')}")
            else:
                logger.warning(f"⚠️ {agent_name}: {data}")
                
        except Exception as e:
            logger.error(f"❌ {agent_name} failed: {e}")

async def test_continuous_data_flow():
    """Test continuous data flow for a specific period"""
    logger.info("\n🧪 Testing Continuous Data Flow")
    logger.info("=" * 60)
    
    # Monitor data flow for 2 minutes
    test_duration = 120  # seconds
    data_updates = []
    
    def data_subscriber(data):
        """Capture data updates"""
        data_updates.append({
            "timestamp": time.time(),
            "type": data.get("type"),
            "symbol": data.get("symbol"),
            "source": data.get("source")
        })
        logger.info(f"📈 Data update: {data.get('symbol')} via {data.get('source')}")
    
    # Subscribe to data updates
    if hasattr(continuous_data_service, 'alert_callbacks'):
        continuous_data_service.alert_callbacks.append(data_subscriber)
    
    logger.info(f"⏳ Monitoring data flow for {test_duration} seconds...")
    start_time = time.time()
    
    while time.time() - start_time < test_duration:
        await asyncio.sleep(10)
        
        current_time = time.time() - start_time
        logger.info(f"⏰ Monitoring progress: {current_time:.0f}s / {test_duration}s")
        logger.info(f"📊 Data updates received: {len(data_updates)}")
    
    logger.success(f"✅ Monitoring complete. Total updates: {len(data_updates)}")
    
    # Analyze data flow
    if data_updates:
        sources = set(update["source"] for update in data_updates if update["source"])
        symbols = set(update["symbol"] for update in data_updates if update["symbol"])
        
        logger.info(f"📊 Data Flow Analysis:")
        logger.info(f"   Sources used: {sources}")
        logger.info(f"   Symbols covered: {symbols}")
        logger.info(f"   Average update rate: {len(data_updates) / (test_duration / 60):.1f} updates/minute")
    
    return len(data_updates) > 0

async def test_custom_session():
    """Test creating and managing custom sessions"""
    logger.info("\n🧪 Testing Custom Session Management")
    logger.info("=" * 60)
    
    session_id = "test_session_1"
    test_symbols = ["INFY", "WIPRO"]
    
    try:
        # Start custom session
        success = await continuous_data_service.start_custom_session(
            session_id=session_id,
            symbols=test_symbols,
            collection_interval=15
        )
        
        if success:
            logger.success(f"✅ Custom session {session_id} started")
            
            # Check session status
            status = continuous_data_service.get_session_status(session_id)
            logger.info(f"📊 Session Status: {json.dumps(status, indent=2)}")
            
            # Wait for some data collection
            await asyncio.sleep(30)
            
            # Stop session
            stop_success = await continuous_data_service.stop_session(session_id)
            if stop_success:
                logger.success(f"✅ Custom session {session_id} stopped")
            else:
                logger.error(f"❌ Failed to stop session {session_id}")
                
            return True
        else:
            logger.error(f"❌ Failed to start custom session {session_id}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Custom session test failed: {e}")
        return False

async def test_http_api_endpoints():
    """Test HTTP API endpoints"""
    logger.info("\n🧪 Testing HTTP API Endpoints")
    logger.info("=" * 60)
    
    base_url = "http://localhost:8000"
    
    endpoints = [
        ("/api/health", "Health Check"),
        ("/api/continuous/status", "Continuous Status"),
        ("/api/stealth/agents", "Stealth Agents"),
        ("/api/stealth/sessions", "Stealth Sessions")
    ]
    
    async with httpx.AsyncClient(timeout=10) as client:
        for endpoint, description in endpoints:
            try:
                logger.info(f"🔍 Testing {description}: {endpoint}")
                response = await client.get(f"{base_url}{endpoint}")
                
                if response.status_code == 200:
                    data = response.json()
                    logger.success(f"✅ {description}: {response.status_code}")
                    logger.debug(f"   Response: {json.dumps(data, indent=2)[:200]}...")
                else:
                    logger.warning(f"⚠️ {description}: {response.status_code}")
                    
            except Exception as e:
                logger.error(f"❌ {description} failed: {e}")

async def test_websocket_streaming():
    """Test WebSocket streaming functionality"""
    logger.info("\n🧪 Testing WebSocket Streaming")
    logger.info("=" * 60)
    
    ws_url = "ws://localhost:8000/api/stealth/stream"
    messages_received = []
    
    try:
        async with websockets.connect(ws_url) as websocket:
            logger.info("🔌 Connected to WebSocket stream")
            
            # Send subscription for a symbol
            await websocket.send("subscribe:RELIANCE")
            logger.info("📡 Subscribed to RELIANCE updates")
            
            # Listen for messages for 30 seconds
            timeout = 30
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(message)
                    messages_received.append(data)
                    
                    logger.info(f"📨 WebSocket message: {data.get('type', 'unknown')}")
                    
                except asyncio.TimeoutError:
                    logger.debug("⏰ WebSocket timeout (normal)")
                    continue
            
            # Unsubscribe
            await websocket.send("unsubscribe:RELIANCE")
            logger.info("📡 Unsubscribed from RELIANCE")
            
        logger.success(f"✅ WebSocket test complete. Messages received: {len(messages_received)}")
        return len(messages_received) > 0
        
    except Exception as e:
        logger.error(f"❌ WebSocket test failed: {e}")
        return False

async def run_comprehensive_test():
    """Run comprehensive test suite"""
    logger.info("🚀 Starting Comprehensive Live Data System Test")
    logger.info("=" * 80)
    
    test_results = {}
    
    # Test 1: Service Initialization
    test_results["initialization"] = await test_continuous_service_initialization()
    
    # Test 2: API Providers
    await test_api_providers()
    
    # Test 3: Stealth Agents
    await test_stealth_agents()
    
    # Test 4: Custom Session Management
    test_results["custom_session"] = await test_custom_session()
    
    # Test 5: HTTP API Endpoints
    await test_http_api_endpoints()
    
    # Test 6: WebSocket Streaming
    test_results["websocket"] = await test_websocket_streaming()
    
    # Test 7: Continuous Data Flow
    test_results["data_flow"] = await test_continuous_data_flow()
    
    # Final Report
    logger.info("\n" + "=" * 80)
    logger.info("🏁 COMPREHENSIVE TEST RESULTS")
    logger.info("=" * 80)
    
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"   {test_name.upper()}: {status}")
    
    overall_success = all(test_results.values())
    
    if overall_success:
        logger.success("🎉 ALL TESTS PASSED - Continuous Live Data System is OPERATIONAL!")
    else:
        logger.error("⚠️ Some tests failed - System needs attention")
    
    return overall_success

if __name__ == "__main__":
    asyncio.run(run_comprehensive_test())
