#!/usr/bin/env python3
"""
Staging environment readiness check script for Zion Market Analysis Platform.
This script checks if the staging environment is ready for testing.
"""
import asyncio
import httpx
import psutil
import time
from datetime import datetime, time as dt_time
from typing import Dict, List, Any

async def check_market_hours() -> bool:
    """Check if current time is within staging hours (4 PM - 8:30 AM IST next day)"""
    current_time = datetime.now().time()
    start = dt_time(16, 0)  # 4 PM
    end = dt_time(8, 30)    # 8:30 AM

    # If end time is earlier than start time, it means the period crosses midnight
    if end < start:
        # Return True if time is after start OR before end
        return current_time >= start or current_time <= end
    else:
        return start <= current_time <= end

async def check_system_resources() -> Dict[str, bool]:
    """Verify system resources meet minimum requirements"""
    return {
        "cpu_available": psutil.cpu_percent(interval=1) < 80,
        "memory_available": psutil.virtual_memory().available > 1024 * 1024 * 1024,  # 1GB
        "disk_space": psutil.disk_usage('/').free > 3 * 1024 * 1024 * 1024  # 3GB minimum
    }

async def check_data_providers(symbols: List[str]) -> Dict[str, bool]:
    """Test data provider connectivity for test symbols"""
    async with httpx.AsyncClient() as client:
        results = {}
        for symbol in symbols:
            try:
                response = await client.get(
                    f"http://localhost:8000/api/market/test/{symbol}",
                    timeout=5.0
                )
                results[symbol] = response.status_code == 200
            except Exception:
                results[symbol] = False
        return results

async def check_monitoring_setup() -> Dict[str, bool]:
    """Verify monitoring infrastructure is ready"""
    async with httpx.AsyncClient() as client:
        try:
            prometheus = await client.get("http://localhost:9090/-/healthy")
            grafana = await client.get("http://localhost:3000/api/health")
            metrics = await client.get("http://localhost:8000/metrics")
            
            return {
                "prometheus": prometheus.status_code == 200,
                "grafana": grafana.status_code == 200,
                "metrics_endpoint": metrics.status_code == 200
            }
        except Exception as e:
            print(f"Monitoring check failed: {e}")
            return {
                "prometheus": False,
                "grafana": False,
                "metrics_endpoint": False
            }

async def main():
    test_symbols = ["TCS", "INFY", "RELIANCE"]
    
    print("🔍 Checking Staging Environment Readiness...")
    
    # Check market hours
    if not await check_market_hours():
        print("❌ Outside staging hours (4 PM - 8:30 AM IST)")
        return False

    # Check system resources
    resources = await check_system_resources()
    if not all(resources.values()):
        print("❌ System resources check failed:")
        for resource, status in resources.items():
            print(f"  - {resource}: {'✅' if status else '❌'}")
        return False

    # Check data providers
    providers = await check_data_providers(test_symbols)
    if not all(providers.values()):
        print("❌ Data provider check failed:")
        for symbol, status in providers.items():
            print(f"  - {symbol}: {'✅' if status else '❌'}")
        return False

    # Check monitoring
    monitoring = await check_monitoring_setup()
    if not all(monitoring.values()):
        print("❌ Monitoring setup check failed:")
        for component, status in monitoring.items():
            print(f"  - {component}: {'✅' if status else '❌'}")
        return False

    print("✅ All checks passed! Staging environment is ready.")
    return True

if __name__ == "__main__":
    asyncio.run(main())