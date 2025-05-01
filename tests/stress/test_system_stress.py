import pytest
import pytest_asyncio
import asyncio
import random
from backend.core.orchestrator import SystemOrchestrator
from backend.utils.monitoring import SystemMonitor
from unittest.mock import AsyncMock
from backend.utils.metrics_collector import MetricsCollector
import time

@pytest.mark.asyncio
class TestSystemStress:
    @pytest_asyncio.fixture
    async def orchestrator(self):
        """Create and properly initialize a SystemOrchestrator instance."""
        monitor = SystemMonitor()
        metrics_collector = MetricsCollector()
        mock_cache_client = AsyncMock()
        instance = SystemOrchestrator(cache_client=mock_cache_client)
        instance.system_monitor = monitor
        instance.metrics_collector = metrics_collector
        # Properly initialize the orchestrator
        await instance.initialize(monitor)
        yield instance
        # Add cleanup if needed
        # await instance.shutdown() # if a shutdown method exists

    async def test_high_concurrency(self, orchestrator):
        """Test system under high concurrency"""
        symbols = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "SBIN.NS"]
        # Run 50 concurrent analyses
        tasks = []
        for _ in range(50):
            symbol = random.choice(symbols)
            tasks.append(orchestrator.analyze_symbol(symbol))
        
        results = await asyncio.gather(*tasks)
        assert len(results) == 50
        assert all(r.get("error") is None for r in results)

    async def test_rapid_sequential(self, orchestrator):
        """Test rapid sequential requests"""
        symbol = "RELIANCE.NS"
        results = []
        for _ in range(20):
            result = await orchestrator.analyze_symbol(symbol)
            results.append(result)
            await asyncio.sleep(0.1)  # Small delay
        
        assert len(results) == 20
        assert all(r["symbol"] == symbol for r in results)

    async def test_memory_usage(self, orchestrator):
        """Test memory usage under load"""
        # Add await
        initial_memory_metrics = await orchestrator.system_monitor.get_health_metrics()
        initial_memory = initial_memory_metrics["system"]["memory_usage"]
        
        # Run multiple analyses
        tasks = [
            orchestrator.analyze_symbol(f"SYMBOL{i}.NS")
            for i in range(100)
        ]
        await asyncio.gather(*tasks)
        
        # Add await
        final_memory_metrics = await orchestrator.system_monitor.get_health_metrics()
        final_memory = final_memory_metrics["system"]["memory_usage"]
        assert final_memory < initial_memory * 2  # Should not double memory usage

    async def test_system_recovery(self, orchestrator):
        """Test system auto-recovery"""
        monitor = SystemMonitor()
        # Add await
        initial_health = await monitor.get_health_metrics()

        # Simulate heavy load
        symbols = ["RELIANCE.NS", "TCS.NS", "INFY.NS"]
        tasks = []
        for _ in range(100):
            tasks.append(orchestrator.analyze_symbol(random.choice(symbols)))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check system recovery
        await asyncio.sleep(5)  # Allow system to recover
        # Add await
        final_health = await monitor.get_health_metrics()
        
        assert final_health["system"]["cpu_usage"] <= initial_health["system"]["cpu_usage"] * 1.5
        assert final_health["components"]["orchestrator"]["status"] == "healthy"

    async def test_cache_effectiveness(self, orchestrator):
        """Test cache hit rates under load"""
        symbol = "RELIANCE.NS"
        # Add await
        start_metrics = await orchestrator.metrics_collector.get_metrics()
        
        # Multiple rapid requests
        tasks = [orchestrator.analyze_symbol(symbol) for _ in range(10)]
        await asyncio.gather(*tasks)
        
        # Add await
        end_metrics = await orchestrator.metrics_collector.get_metrics()
        cache_hit_ratio = end_metrics["performance"]["cache_hit_ratio"]
        assert cache_hit_ratio > 0.7  # Expect >70% cache hits

    async def test_parallel_category_execution(self, orchestrator):
        """Test parallel category execution efficiency"""
        start_time = time.time()
        result = await orchestrator.analyze_symbol("RELIANCE.NS")
        execution_time = time.time() - start_time
        
        assert execution_time < 10  # Should complete within 10 seconds
        assert all(cat in result["category_results"] for cat in [
            "TECHNICAL", "VALUATION", "MARKET", "RISK"
        ])

