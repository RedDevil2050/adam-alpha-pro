import pytest
import pytest_asyncio
import asyncio
from backend.core.orchestrator import SystemOrchestrator
from backend.agents.categories import CategoryType
# Correct the import path for SystemMonitor
from backend.utils.system_monitor import SystemMonitor
from backend.utils.metrics_collector import MetricsCollector
# Import the mocked redis client utility
from backend.utils.cache_utils import get_redis_client

@pytest.mark.asyncio
class TestSystemIntegration:
    @pytest_asyncio.fixture
    async def orchestrator(self):
        """Create and properly initialize a SystemOrchestrator instance."""
        monitor = SystemMonitor()
        # Get the mocked cache client
        cache_client = await get_redis_client()
        # Pass the cache_client to the constructor
        instance = SystemOrchestrator(cache_client=cache_client)
        # Properly initialize the orchestrator
        await instance.initialize(monitor)
        yield instance
        # Add cleanup if needed
        # await instance.shutdown() # if a shutdown method exists

    async def test_full_analysis_flow(self, orchestrator):
        """Test complete analysis pipeline"""
        # Initialize MetricsCollector - Assuming it doesn't need complex setup for this test
        metrics_collector = MetricsCollector()
        monitor = SystemMonitor() # Assuming a fresh monitor per test is okay

        # Pass monitor and metrics_collector to analyze_symbol
        result = await orchestrator.analyze_symbol(
            symbol="RELIANCE.NS",
            monitor=monitor,
            metrics_collector=metrics_collector
        )
        
        # Verify basic structure
        assert result["symbol"] == "RELIANCE.NS"
        assert "verdict" in result
        assert "category_results" in result
        assert "system_health" in result
        
        # Verify all required categories executed
        categories = result["category_results"].keys()
        assert CategoryType.VALUATION.value in categories
        assert CategoryType.TECHNICAL.value in categories
        assert CategoryType.MARKET.value in categories
        assert CategoryType.RISK.value in categories

        # Verify health metrics
        health = result["system_health"]
        assert health["system"]["cpu_usage"] >= 0
        assert health["system"]["memory_usage"] >= 0

    async def test_parallel_analysis(self, orchestrator):
        """Test system under parallel load"""
        symbols = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS"]
        # Initialize MetricsCollector and Monitor - Assuming shared instances are okay for parallel test
        metrics_collector = MetricsCollector()
        monitor = SystemMonitor()

        tasks = [
            orchestrator.analyze_symbol(
                symbol=symbol,
                monitor=monitor,
                metrics_collector=metrics_collector
            ) for symbol in symbols
        ]
        results = await asyncio.gather(*tasks)
        
        assert len(results) == len(symbols)
        assert all("verdict" in r for r in results)
        assert all("system_health" in r for r in results)

    async def test_error_handling(self, orchestrator):
        """Test system error handling"""
        metrics_collector = MetricsCollector()
        monitor = SystemMonitor()
        result = await orchestrator.analyze_symbol(
            symbol="INVALID_SYMBOL",
            monitor=monitor,
            metrics_collector=metrics_collector
        )
        assert "error" in result
        # Check component status via the monitor instance used in the call
        health_metrics = await monitor.get_health_metrics()
        assert health_metrics["components"]["orchestrator"]["status"] == "healthy"

    async def test_caching_mechanism(self, orchestrator):
        """Test caching behavior"""
        metrics_collector = MetricsCollector()
        monitor = SystemMonitor()
        # First call
        result1 = await orchestrator.analyze_symbol(
            symbol="SBIN.NS",
            monitor=monitor,
            metrics_collector=metrics_collector
        )
        # Second call should use cache
        # Use separate monitor/collector if needed to isolate metrics, or reuse if appropriate
        result2 = await orchestrator.analyze_symbol(
            symbol="SBIN.NS",
            monitor=monitor, # Reusing monitor
            metrics_collector=metrics_collector # Reusing collector
        )
        
        assert result1["verdict"] == result2["verdict"]
        assert result1["analysis_id"] != result2["analysis_id"]

    async def test_market_regime_awareness(self, orchestrator):
        """Test market regime adaptation"""
        metrics_collector = MetricsCollector()
        monitor = SystemMonitor()
        result = await orchestrator.analyze_symbol(
            symbol="RELIANCE.NS",
            monitor=monitor,
            metrics_collector=metrics_collector
        )
        assert "market_regime" in str(result["category_results"])

    async def test_system_recovery(self, orchestrator):
        """Test system recovery from failures"""
        metrics_collector = MetricsCollector()
        monitor = SystemMonitor() # Use a single monitor instance for the recovery test
        # Simulate multiple failures and verify recovery
        for _ in range(3):
            result = await orchestrator.analyze_symbol(
                symbol="INVALID_SYMBOL",
                monitor=monitor,
                metrics_collector=metrics_collector
            )
            # Access health metrics directly from the monitor instance used
            health_metrics = await monitor.get_health_metrics()
            # Check system status, not orchestrator component status specifically
            assert health_metrics["system"]["status"] != "error" # System should remain operational

    async def test_metrics_collection(self, orchestrator):
        """Test metrics collection"""
        metrics_collector = MetricsCollector() # Create collector for this test
        monitor = SystemMonitor()
        await orchestrator.analyze_symbol(
            symbol="RELIANCE.NS",
            monitor=monitor,
            metrics_collector=metrics_collector # Pass the collector
        )
        # Get metrics from the collector instance used
        metrics = metrics_collector.get_metrics()
        
        assert "performance" in metrics
        assert "category_stats" in metrics
        assert metrics["performance"]["avg_response_time"] > 0
