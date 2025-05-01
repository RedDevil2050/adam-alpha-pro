import pytest
import pytest_asyncio
import asyncio
import logging
from backend.core.orchestrator import SystemOrchestrator
from backend.agents.categories import CategoryType
# Correct the import path for SystemMonitor
from backend.utils.system_monitor import SystemMonitor
from backend.utils.metrics_collector import MetricsCollector
# Import the mocked redis client utility
from backend.utils.cache_utils import get_redis_client

# Configure logger
logger = logging.getLogger(__name__)

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
        # metrics_collector = MetricsCollector() # Collector is internal to orchestrator now
        monitor = SystemMonitor() # Assuming a fresh monitor per test is okay

        # Pass monitor to analyze_symbol (metrics_collector is internal)
        result = await orchestrator.analyze_symbol(
            symbol="RELIANCE.NS",
            monitor=monitor
            # metrics_collector=metrics_collector # Removed
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
        # Initialize Monitor - Assuming shared instance is okay for parallel test
        # metrics_collector = MetricsCollector() # Collector is internal
        monitor = SystemMonitor()

        tasks = [
            orchestrator.analyze_symbol(
                symbol=symbol,
                monitor=monitor
                # metrics_collector=metrics_collector # Removed
            ) for symbol in symbols
        ]
        results = await asyncio.gather(*tasks)
        
        assert len(results) == len(symbols)
        assert all("verdict" in r for r in results)
        assert all("system_health" in r for r in results)

    async def test_error_handling(self, orchestrator):
        """Test system error handling"""
        # metrics_collector = MetricsCollector() # Collector is internal
        monitor = SystemMonitor()
        result = await orchestrator.analyze_symbol(
            symbol="INVALID_SYMBOL",
            monitor=monitor
            # metrics_collector=metrics_collector # Removed
        )

        # Assert that the overall analysis didn't crash and returned a result
        assert result is not None
        assert result.get("symbol") == "INVALID_SYMBOL"

        # Check if the top-level error field indicates a failure (optional, depends on orchestrator logic)
        # assert result.get("error") is not None

        # Check that category results are present
        assert "category_results" in result

        # Find a category that is expected to fail due to the invalid symbol (e.g., RISK or TECHNICAL)
        # Let's assume RISK category agents rely on data fetching that fails for INVALID_SYMBOL
        risk_results_data = result.get("category_results", {}).get(CategoryType.RISK.value)
        assert risk_results_data is not None, f"Expected results for category '{CategoryType.RISK.value}'"

        # Check if the category itself reported an error or contained agent errors
        category_had_errors = risk_results_data.get("error") or any(agent_res.get("status") == 'error' for agent_res in risk_results_data.get("results", []))
        assert category_had_errors, f"Expected errors within the '{CategoryType.RISK.value}' category results for INVALID_SYMBOL"

        # Optionally, check a specific agent known to fail (e.g., beta_agent)
        beta_agent_result = next((res for res in risk_results_data.get("results", []) if res.get("agent_name") == 'beta_agent'), None)
        if beta_agent_result: # Agent might not be present if import failed, etc.
            assert beta_agent_result.get("status") == "error"
            # Check for specific error message if needed (might be fragile)
            # assert "ValueError" in beta_agent_result.get("error", "")

        # Check component status via the monitor instance used in the call
        health_metrics = monitor.get_health_metrics()
        assert health_metrics["component_statuses"]["orchestrator"] == "healthy", "Orchestrator component should remain healthy despite symbol errors"

    async def test_caching_mechanism(self, orchestrator):
        """Test caching behavior"""
        # metrics_collector = MetricsCollector() # Collector is internal
        monitor = SystemMonitor()
        symbol_to_test = "SBIN.NS"
        cache_client = await get_redis_client() # Get client to clear cache first
        await cache_client.delete(f"analysis:{symbol_to_test}") # Clear potential stale cache
        # First call
        result1 = await orchestrator.analyze_symbol(
            symbol=symbol_to_test,
            monitor=monitor
            # metrics_collector=metrics_collector # Removed
        )
        # Second call should use cache
        # Use separate monitor if needed to isolate metrics, or reuse if appropriate
        result2 = await orchestrator.analyze_symbol(
            symbol=symbol_to_test,
            monitor=monitor # Reusing monitor
            # metrics_collector=metrics_collector # Removed
        )
        
        assert result1["verdict"] == result2["verdict"]
        assert result1["analysis_id"] != result2["analysis_id"]
        # Add assertion to confirm cache was hit (e.g., by checking logs or mocking cache get)
        # This requires more advanced mocking or log inspection, skipping for now.

    async def test_market_regime_awareness(self, orchestrator):
        """Test market regime adaptation"""
        # metrics_collector = MetricsCollector() # Collector is internal
        monitor = SystemMonitor()
        result = await orchestrator.analyze_symbol(
            symbol="RELIANCE.NS",
            monitor=monitor
            # metrics_collector=metrics_collector # Removed
        )
        # Check if market category results exist and contain regime info
        market_results = result.get("category_results", {}).get(CategoryType.MARKET.value)
        assert market_results, "Market category results should be present"
        # Check within the 'results' list of the market category data
        assert any("market_regime" in agent_res.get("details", {}) for agent_res in market_results.get("results", [])), "Market regime details expected in market agent results"

    async def test_system_recovery(self, orchestrator):
        """Test system recovery from failures"""
        # metrics_collector = MetricsCollector() # Collector is internal
        monitor = SystemMonitor() # Use a single monitor instance for the recovery test
        # Simulate multiple failures and verify recovery
        for i in range(3):
            logger.debug(f"System Recovery Test: Iteration {i+1}")
            result = await orchestrator.analyze_symbol(
                symbol="INVALID_SYMBOL",
                monitor=monitor
                # metrics_collector=metrics_collector # Removed
            )
            # Access health metrics directly from the monitor instance used
            # Corrected: get_health_metrics is not async
            health_metrics = monitor.get_health_metrics()
            # Check overall system status if available, or component statuses
            # Assuming orchestrator should remain healthy despite symbol errors
            assert health_metrics["component_statuses"]["orchestrator"] == "healthy", f"Orchestrator should be healthy on iteration {i+1}"
            # Check if system metrics are still being reported
            assert health_metrics["system"]["cpu_usage"] is not None
            assert health_metrics["system"]["memory_usage"] is not None

    async def test_metrics_collection(self, orchestrator):
        """Test metrics collection"""
        # metrics_collector = MetricsCollector() # Collector is internal now
        monitor = SystemMonitor()
        result = await orchestrator.analyze_symbol( # Call analyze_symbol
            symbol="RELIANCE.NS",
            monitor=monitor
            # metrics_collector=metrics_collector # Removed
        )
        # Get metrics from the result, as collector is internal
        metrics = result.get("execution_metrics", {}) # Access metrics from result
        
        assert "performance" in metrics
        assert "category_stats" in metrics
        # Check if avg_response_time exists and is > 0, handle potential None
        assert metrics.get("performance", {}).get("avg_response_time", 0) > 0
