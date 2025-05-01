import pytest
import pytest_asyncio
import asyncio
from backend.core.orchestrator import SystemOrchestrator
from backend.agents.categories import CategoryType
from backend.utils.monitoring import SystemMonitor
from backend.utils.metrics_collector import MetricsCollector

@pytest.mark.asyncio
class TestSystemIntegration:
    @pytest_asyncio.fixture
    async def orchestrator(self):
        """Create and properly initialize a SystemOrchestrator instance."""
        monitor = SystemMonitor()
        instance = SystemOrchestrator()
        # Properly initialize the orchestrator
        await instance.initialize(monitor)
        yield instance
        # Add cleanup if needed
        # await instance.shutdown() # if a shutdown method exists

    async def test_full_analysis_flow(self, orchestrator):
        """Test complete analysis pipeline"""
        result = await orchestrator.analyze_symbol("RELIANCE.NS")
        
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
        tasks = [orchestrator.analyze_symbol(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks)
        
        assert len(results) == len(symbols)
        assert all("verdict" in r for r in results)
        assert all("system_health" in r for r in results)

    async def test_error_handling(self, orchestrator):
        """Test system error handling"""
        result = await orchestrator.analyze_symbol("INVALID_SYMBOL")
        assert "error" in result
        assert result["system_health"]["components"]["orchestrator"]["status"] == "healthy"

    async def test_caching_mechanism(self, orchestrator):
        """Test caching behavior"""
        # First call
        result1 = await orchestrator.analyze_symbol("SBIN.NS")
        # Second call should use cache
        result2 = await orchestrator.analyze_symbol("SBIN.NS")
        
        assert result1["verdict"] == result2["verdict"]
        assert result1["analysis_id"] != result2["analysis_id"]

    async def test_market_regime_awareness(self, orchestrator):
        """Test market regime adaptation"""
        result = await orchestrator.analyze_symbol("RELIANCE.NS")
        assert "market_regime" in str(result["category_results"])

    async def test_system_recovery(self, orchestrator):
        """Test system recovery from failures"""
        # Simulate multiple failures and verify recovery
        for _ in range(3):
            result = await orchestrator.analyze_symbol("INVALID_SYMBOL")
            health_metrics = await orchestrator.system_monitor.get_health_metrics()
            assert health_metrics["system"]["status"] != "error"

    async def test_metrics_collection(self, orchestrator):
        """Test metrics collection"""
        await orchestrator.analyze_symbol("RELIANCE.NS")
        metrics = orchestrator.metrics_collector.get_metrics()
        
        assert "performance" in metrics
        assert "category_stats" in metrics
        assert metrics["performance"]["avg_response_time"] > 0
