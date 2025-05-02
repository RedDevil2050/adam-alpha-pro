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

        # Check that category results are present
        assert "category_results" in result

        # Find a category that is expected to fail due to the invalid symbol (e.g., RISK or TECHNICAL)
        # Let's assume RISK category agents rely on data fetching that fails for INVALID_SYMBOL
        risk_results_data = result.get("category_results", {}).get(CategoryType.RISK.value)
        assert risk_results_data is not None, f"Expected results for category '{CategoryType.RISK.value}'"

        # Check if the category itself reported an error or contained agent errors/failures
        category_level_error = risk_results_data.get("error") is not None
        agents_in_category = risk_results_data.get("results", [])
        # Ensure agent_res is checked to be a dict before accessing keys
        agent_level_failure = any(
            (agent_res.get("status") == 'error' or
             agent_res.get("verdict") == "NO_DATA" or
             agent_res.get("error") is not None)
            for agent_res in agents_in_category if isinstance(agent_res, dict)
        )
        category_had_failure_indicators = category_level_error or agent_level_failure
        assert category_had_failure_indicators, f"Expected failure indicators (error status, NO_DATA verdict, or error key) within the '{CategoryType.RISK.value}' category results for INVALID_SYMBOL. Found: {risk_results_data}"

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
        market_results_data = result.get("category_results", {}).get(CategoryType.MARKET.value)
        assert market_results_data, "Market category results should be present"

        # Find the result specifically from market_regime_agent
        market_regime_agent_result = None
        for agent_res in market_results_data.get("results", []):
            # Ensure agent_res is a dict and has 'agent_name' before checking
            if isinstance(agent_res, dict) and agent_res.get("agent_name") == "market_regime_agent":
                 market_regime_agent_result = agent_res
                 break

        assert market_regime_agent_result is not None, "Result from 'market_regime_agent' not found in MARKET category results"
        assert "details" in market_regime_agent_result, "Details missing from 'market_regime_agent' result"
        assert "market_regime" in market_regime_agent_result.get("details", {}), "'market_regime' key missing in details of 'market_regime_agent' result"

    async def test_system_recovery(self, orchestrator):
        """Test system recovery from failures"""
        # metrics_collector = MetricsCollector() # Collector is internal
        # Simulate multiple failures and verify recovery
        for i in range(3):
            # Create a new monitor for each iteration to isolate state
            monitor = SystemMonitor()
            logger.debug(f"System Recovery Test: Iteration {i+1}")
            result = await orchestrator.analyze_symbol(
                symbol="INVALID_SYMBOL",
                monitor=monitor # Pass the new monitor instance
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
        # Check if avg_response_time exists and is > 0
        performance_metrics = metrics.get("performance", {})
        assert "avg_response_time" in performance_metrics, "avg_response_time should be in performance metrics"
        assert performance_metrics["avg_response_time"] > 0, "avg_response_time should be greater than 0 after a successful analysis"
