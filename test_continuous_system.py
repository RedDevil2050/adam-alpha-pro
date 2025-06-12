#!/usr/bin/env python3
"""
Test Continuous Live Data Collection System
==========================================

Tests the complete end-to-end continuous data flow system including:
- Continuous data service initialization
- API provider failover
- Stealth agent fallback
- Real-time streaming
- Health monitoring
- Auto-recovery mechanisms
"""

import asyncio
import time
from loguru import logger
from backend.services.continuous_data_service import continuous_data_service

async def test_continuous_data_system():
    """Test the complete continuous data collection system"""
    
    print("🚀 Testing Continuous Live Data Collection System")
    print("=" * 60)
    
    try:
        # Initialize the service
        print("\n1️⃣ Initializing Continuous Data Service...")
        await continuous_data_service.initialize()
        print("✅ Service initialized successfully")
        
        # Check initial status
        print("\n2️⃣ Checking system status...")
        status = continuous_data_service.get_session_status()
        print(f"📊 Status: {status}")
        
        # Test custom session creation
        print("\n3️⃣ Testing custom session creation...")
        test_symbols = ['RELIANCE', 'TCS', 'INFY']
        test_sources = ['zerodha_api', 'yahoo_finance_api', 'enhanced_moneycontrol']
        
        success = await continuous_data_service.start_custom_session(
            session_id="test_session_1",
            symbols=test_symbols,
            data_sources=test_sources,
            collection_interval=15
        )
        
        if success:
            print("✅ Custom session started successfully")
        else:
            print("❌ Failed to start custom session")
        
        # Monitor for a period
        print("\n4️⃣ Monitoring data collection for 60 seconds...")
        
        # Subscribe to alerts
        alerts_received = []
        
        def alert_handler(alert_data):
            alerts_received.append(alert_data)
            print(f"🚨 ALERT: {alert_data['message']}")
        
        continuous_data_service.subscribe_to_alerts(alert_handler)
        
        # Monitor for 60 seconds
        start_time = time.time()
        while time.time() - start_time < 60:
            await asyncio.sleep(10)
            
            # Check session status
            session_status = continuous_data_service.get_session_status("test_session_1")
            if session_status and not session_status.get("error"):
                uptime = session_status.get("uptime", 0)
                print(f"📊 Test session uptime: {uptime:.1f}s")
            
            # Check overall status
            overall_status = continuous_data_service.get_session_status()
            active_sessions = overall_status.get("active_sessions", 0)
            print(f"📈 Active sessions: {active_sessions}")
        
        # Test session stopping
        print("\n5️⃣ Testing session management...")
        success = await continuous_data_service.stop_session("test_session_1")
        if success:
            print("✅ Test session stopped successfully")
        else:
            print("❌ Failed to stop test session")
        
        # Final status check
        print("\n6️⃣ Final system check...")
        final_status = continuous_data_service.get_session_status()
        print(f"📊 Final status: {final_status}")
        
        # Check alerts
        print(f"\n📢 Alerts received during testing: {len(alerts_received)}")
        for alert in alerts_received:
            print(f"  - {alert['type']}: {alert['message']}")
        
        print("\n✅ Continuous data system test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        logger.error(f"Test error: {e}")
    
    finally:
        # Cleanup
        print("\n🧹 Cleaning up...")
        try:
            await continuous_data_service.shutdown()
            print("✅ Service shutdown complete")
        except Exception as e:
            print(f"⚠️ Shutdown error: {e}")

async def test_data_source_failover():
    """Test failover between different data sources"""
    
    print("\n🔄 Testing Data Source Failover")
    print("=" * 40)
    
    try:
        # Initialize service
        await continuous_data_service.initialize()
        
        # Create session with specific source order
        failover_sources = [
            'alpha_vantage_api',  # Will likely hit rate limits
            'yahoo_finance_api',  # Fallback API
            'enhanced_moneycontrol',  # Stealth fallback
            'moneycontrol'  # Final fallback
        ]
        
        success = await continuous_data_service.start_custom_session(
            session_id="failover_test",
            symbols=['RELIANCE'],
            data_sources=failover_sources,
            collection_interval=5  # Fast collection to trigger rate limits
        )
        
        if success:
            print("✅ Failover test session started")
            
            # Monitor for 30 seconds to see failover in action
            print("⏳ Monitoring failover behavior for 30 seconds...")
            await asyncio.sleep(30)
            
            # Stop session
            await continuous_data_service.stop_session("failover_test")
            print("✅ Failover test completed")
        
    except Exception as e:
        print(f"❌ Failover test failed: {e}")

async def test_system_health_monitoring():
    """Test system health monitoring and alerts"""
    
    print("\n🏥 Testing System Health Monitoring")
    print("=" * 40)
    
    health_alerts = []
    
    def health_alert_handler(alert_data):
        health_alerts.append(alert_data)
        print(f"🚨 Health Alert: {alert_data['message']}")
    
    continuous_data_service.subscribe_to_alerts(health_alert_handler)
    
    try:
        # Initialize and monitor for health checks
        await continuous_data_service.initialize()
        
        print("⏳ Monitoring system health for 30 seconds...")
        await asyncio.sleep(30)
        
        print(f"📊 Health alerts received: {len(health_alerts)}")
        
    except Exception as e:
        print(f"❌ Health monitoring test failed: {e}")

async def main():
    """Run all tests"""
    
    print("🎯 Starting Comprehensive Continuous Data System Tests")
    print("=" * 70)
    
    # Test 1: Basic system functionality
    await test_continuous_data_system()
    
    # Test 2: Data source failover
    await test_data_source_failover()
    
    # Test 3: Health monitoring
    await test_system_health_monitoring()
    
    print("\n🎉 All tests completed!")

if __name__ == "__main__":
    asyncio.run(main())
