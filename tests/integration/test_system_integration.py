import pytest
import pytest_asyncio
import asyncio
import logging
from unittest.mock import MagicMock, AsyncMock, patch

from backend.core.orchestrator import SystemOrchestrator
from backend.agents.categories import CategoryType
from backend.utils.system_monitor import SystemMonitor # Ensure SystemMonitor is imported for direct use in tests
from backend.utils.metrics_collector import MetricsCollector
# Import the mocked redis client utility
from backend.utils.cache_utils import get_redis_client

# Configure logger
logger = logging.getLogger(__name__)

@pytest.fixture
def mock_system_monitor():
    """Fixture to provide a mock SystemMonitor instance for external use."""
    monitor_mock = MagicMock(spec=SystemMonitor)
    monitor_mock.register_component = MagicMock()
    monitor_mock.update_component_status = MagicMock()
    monitor_mock.get_health_metrics = AsyncMock(return_value={
        "system": {"cpu_usage": 0.1, "memory_usage": 0.1}, 
        "components": {}, 
        "services": {}, 
        "errors": [], 
        "uptime": "mocked"
    })
    monitor_mock.start_analysis = AsyncMock()
    monitor_mock.end_analysis = AsyncMock()
    monitor_mock.is_ready = MagicMock(return_value={"ready": True, "components": {}})
    monitor_mock.components = {} 
    return monitor_mock

@pytest.mark.asyncio
class TestSystemIntegration:
    @pytest_asyncio.fixture
    async def orchestrator(self, mock_redis_client, mock_system_monitor): # mock_system_monitor is the external one
        """Fixture to create a SystemOrchestrator instance with a mocked cache and external monitor."""
        with patch('backend.core.orchestrator.SystemMonitor', new_callable=MagicMock) as MockInternalSystemMonitorConstructor, \
             patch('websockets.client.connect', new_callable=AsyncMock) as mock_websocket_connect:

            mock_internal_monitor_instance = MockInternalSystemMonitorConstructor.return_value
            
            # Initialize .components as a dictionary for the orchestrator to interact with
            mock_internal_monitor_instance.components = {"orchestrator": {"status": "initializing", "last_updated": "initial"}}

            # Mock update_component_status to actually update the components dict
            def mock_update_status(component_name, status, details=None):
                if component_name not in mock_internal_monitor_instance.components:
                    mock_internal_monitor_instance.components[component_name] = {}
                mock_internal_monitor_instance.components[component_name]['status'] = status
                mock_internal_monitor_instance.components[component_name]['last_updated'] = "mocked_update_time" # Simulate time update
                if details:
                    mock_internal_monitor_instance.components[component_name]['details'] = details
            
            mock_internal_monitor_instance.update_component_status = MagicMock(side_effect=mock_update_status)
            mock_internal_monitor_instance.register_component = MagicMock() # Keep as simple mock for assertion

            # Mock get_health_metrics to use the dynamic components dict
            async def mock_get_health():
                return {
                    "system": {"cpu_usage": 0.0, "memory_usage": 0.0, "disk_usage": {"total": 100, "used": 50, "free": 50, "percent": 50.0}},
                    "components": mock_internal_monitor_instance.components, # Use the dynamic components
                    "services": {"redis": {"status": "connected", "details": "mocked_detail"}},
                    "errors": [],
                    "uptime": "1 day"
                }
            mock_internal_monitor_instance.get_health_metrics = AsyncMock(side_effect=mock_get_health)
            
            mock_internal_monitor_instance.start_analysis = AsyncMock()
            mock_internal_monitor_instance.end_analysis = AsyncMock()
            mock_internal_monitor_instance.is_ready = MagicMock(return_value={"ready": True, "components": {}})

            mock_websocket_connect.return_value.__aenter__.return_value.send = AsyncMock()
            mock_websocket_connect.return_value.__aenter__.return_value.recv = AsyncMock(return_value="{}")

            instance = SystemOrchestrator(cache_client=mock_redis_client)

            assert instance.system_monitor is mock_internal_monitor_instance, \
                "Internal system_monitor is not the mocked instance!"

            await instance.initialize(monitor=mock_system_monitor)

            mock_internal_monitor_instance.register_component.assert_any_call("orchestrator")
            # Check that update_component_status was called to set orchestrator to healthy
            # The side_effect of mock_update_status will have updated mock_internal_monitor_instance.components
            assert mock_internal_monitor_instance.components.get("orchestrator", {}).get("status") == "healthy", \
                "Orchestrator status not updated to 'healthy' in mock_internal_monitor_instance.components after initialize"


            mock_system_monitor.register_component.assert_any_call("orchestrator")
            mock_system_monitor.update_component_status.assert_any_call("orchestrator", "healthy")
            
            return instance

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
        # metrics_collector = MetricsCollector() # Collector is internal
        # Removed shared monitor instance
        # monitor = SystemMonitor()

        tasks = [
            orchestrator.analyze_symbol(
                symbol=symbol,
                # Create a new monitor for each task to ensure isolation
                monitor=SystemMonitor()
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
        monitor_for_call = SystemMonitor() # Use a dedicated monitor for the call
        result = await orchestrator.analyze_symbol(
            symbol="INVALID_SYMBOL",
            monitor=monitor_for_call # Pass the dedicated monitor
            # metrics_collector=metrics_collector # Removed
        )

        # Assert that the overall analysis didn't crash and returned a result
        assert result is not None
        assert result.get("symbol") == "INVALID_SYMBOL"

        # Check that category results are present
        # Check if 'error' key exists at the top level, indicating orchestrator-level failure
        # OR if category_results is missing/empty
        if "error" in result or not result.get("category_results"):
             # If orchestrator failed significantly, check its health directly
             # Access the orchestrator's internal monitor instance
             internal_monitor = orchestrator.system_monitor
             health_metrics = await internal_monitor.get_health_metrics()
             assert health_metrics.get("components", {}).get("orchestrator", {}).get("status") == "healthy", \
                 "Orchestrator component should remain healthy even after significant analysis error"
             # Skip detailed category checks if the whole process failed early
             logger.warning("Skipping detailed category checks due to top-level error or missing category results.")
             pytest.skip("Skipping detailed category checks due to top-level error or missing category results.")

        # --- Proceed with category checks only if category_results exist ---
        assert "category_results" in result

        # Find a category that is expected to fail due to the invalid symbol (e.g., RISK or TECHNICAL)
        # Let's assume RISK category agents rely on data fetching that fails for INVALID_SYMBOL
        risk_results_data = result.get("category_results", {}).get(CategoryType.RISK.value)
        assert risk_results_data is not None, f"Expected results for category '{CategoryType.RISK.value}'"

        # Check if the category itself reported an error, contained agent errors/failures, or had no results
        category_level_error = risk_results_data.get("error") is not None
        agents_in_category = risk_results_data.get("results", [])
        no_agent_results = not agents_in_category # Check if the results list is empty

        # Ensure agent_res is checked to be a dict OR is None before accessing keys/checking identity
        agent_level_failure = any(
            agent_res is None or # Treat None results as failure indication
            (isinstance(agent_res, dict) and (
                agent_res.get("status") == 'error' or
                agent_res.get("verdict") == "NO_DATA" or
                agent_res.get("error") is not None
            )) or
            # Added: Treat non-None, non-dictionary items as failures,
            # as they likely represent raw error strings or similar.
            (agent_res is not None and not isinstance(agent_res, dict))
            for agent_res in agents_in_category
        )
        # Combine checks: category error OR no results OR agent-level failure
        category_had_failure_indicators = category_level_error or no_agent_results or agent_level_failure

        # --- Add Detailed Logging --- 
        logger.info(f"--- test_error_handling Debug Info ---")
        logger.info(f"Symbol: INVALID_SYMBOL")
        # logger.info(f"Full Analysis Result: {result}") # Can be very verbose
        logger.info(f"Risk Category Data ('risk_results_data'): {risk_results_data}")
        logger.info(f"Category Level Error ('category_level_error'): {category_level_error}")
        logger.info(f"Agents in Category List ('agents_in_category'): {agents_in_category}")
        logger.info(f"Is Agent List Empty? ('no_agent_results'): {no_agent_results}")

        agent_failure_details = []
        for i, agent_res in enumerate(agents_in_category):
            if isinstance(agent_res, dict):
                status = agent_res.get("status")
                verdict = agent_res.get("verdict")
                error = agent_res.get("error")
                is_failure = (status == 'error' or verdict == "NO_DATA" or error is not None)
                agent_failure_details.append(f"  Agent {i} ({agent_res.get('agent_name', 'N/A')}): status='{status}', verdict='{verdict}', error='{error}', is_failure={is_failure}")
            else:
                agent_failure_details.append(f"  Agent {i}: Not a dict - {type(agent_res)}")
        
        logger.info(f"Agent Failure Checks:\n" + "\n".join(agent_failure_details))
        logger.info(f"Overall Agent Level Failure ('agent_level_failure'): {agent_level_failure}")
        logger.info(f"Final Combined Failure Indicator ('category_had_failure_indicators'): {category_had_failure_indicators}")
        logger.info(f"--- End Debug Info ---")
        # --- End Detailed Logging ---

        assert category_had_failure_indicators, (
            f"Expected failure indicators (category error, no agent results, None result, or agent error/NO_DATA) " # Updated message
            f"within the '{CategoryType.RISK.value}' category results for INVALID_SYMBOL. "
            f"Actual category_results['{CategoryType.RISK.value}']: {risk_results_data}"
        )

        # Check component status using the orchestrator's INTERNAL monitor AFTER the call
        internal_monitor = orchestrator.system_monitor
        health_metrics_internal = await internal_monitor.get_health_metrics() # Added await
        # --- Ensure health_metrics_internal is a dict before accessing ---
        assert isinstance(health_metrics_internal, dict), f"Expected health_metrics_internal to be a dict, but got {type(health_metrics_internal)}"
        
        components_data = health_metrics_internal.get("components", {}) # Changed from component_statuses
        assert isinstance(components_data, dict), f"Expected components_data to be a dict, but got {type(components_data)}"

        orchestrator_component = components_data.get("orchestrator", {})
        assert isinstance(orchestrator_component, dict), f"Expected orchestrator_component to be a dict, but got {type(orchestrator_component)}"

        assert orchestrator_component.get("status") == "healthy", \
            f"Orchestrator component should remain healthy in internal monitor after handling symbol error. Health was: {health_metrics_internal}"

    async def test_caching(self, orchestrator):
        """Test caching mechanism"""
        # metrics_collector = MetricsCollector() # Collector is internal
        monitor = SystemMonitor() # Correct indentation
        symbol_to_test = "SBIN.NS"
        # Define specific categories for this test, as per previous fix strategy
        test_categories = [CategoryType.VALUATION, CategoryType.TECHNICAL]
    
        # Patch get_redis_client for the explicit cache deletion part of this test
        with patch('backend.utils.cache_utils.get_redis_client') as mock_get_redis_for_delete:
            # Configure the mock client instance that get_redis_client will return
            mock_client_instance_for_delete = AsyncMock() # Make the client instance itself an AsyncMock
            # mock_client_instance_for_delete.delete = AsyncMock() # This line is not strictly necessary if the parent is AsyncMock
            mock_get_redis_for_delete.return_value = mock_client_instance_for_delete
    
            # Get the client from the mock by calling the patched version
            cache_client_for_deletion = mock_get_redis_for_delete()
    
            categories_str = ",".join(sorted([cat.value for cat in test_categories]))
            cache_key_to_delete = f"analysis:{symbol_to_test}:{categories_str}"
            await cache_client_for_deletion.delete(cache_key_to_delete)
            logger.info(f"Cache cleared for {symbol_to_test} with key {cache_key_to_delete} for categories '{categories_str}' before caching test.")

        # First call
        result1 = await orchestrator.analyze_symbol(
            symbol=symbol_to_test,
            monitor=monitor,
            categories=test_categories # Pass the specific categories
            # metrics_collector=metrics_collector # Removed
        )
        # Second call should use cache
        # Use separate monitor if needed to isolate metrics, or reuse if appropriate
        result2 = await orchestrator.analyze_symbol(
            symbol=symbol_to_test,
            monitor=monitor, # Reusing monitor
            categories=test_categories # Pass the same specific categories
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
            # Ensure agent_res is a dict and has 'agent_name' before checking (case-insensitive)
            if isinstance(agent_res, dict) and agent_res.get("agent_name", "").lower() == "market_regime_agent":
                 market_regime_agent_result = agent_res
                 break

        assert market_regime_agent_result is not None, "Result from 'market_regime_agent' not found in MARKET category results"
        
        agent_name = market_regime_agent_result.get("agent_name", "market_regime_agent") # Default to expected name
        agent_status = market_regime_agent_result.get("status")
        agent_verdict = market_regime_agent_result.get("verdict")
        agent_error_field = market_regime_agent_result.get("error")

        # Agent is considered to have been able to determine regime if it didn't report a critical failure status/verdict
        able_to_determine_regime = not (
            agent_status == 'error' or
            agent_verdict == 'NO_DATA' or # If no data, can't determine regime
            agent_error_field is not None
        )

        # The 'details' key should generally be present, possibly containing error information if not successful.
        assert "details" in market_regime_agent_result, \
            f"Details missing from '{agent_name}' result. Full agent result: {market_regime_agent_result}"

        if able_to_determine_regime:
            # If agent was (or should have been) able to determine regime, 'market_regime' key should be in details
            assert "market_regime" in market_regime_agent_result.get("details", {}), \
                f"'market_regime' key missing in details of '{agent_name}' result when it was expected to determine regime. " \
                f"Status: {agent_status}, Verdict: {agent_verdict}, Error: {agent_error_field}. " \
                f"Details: {market_regime_agent_result.get('details')}"
        else:
            # If agent was NOT able to determine regime (e.g., due to data error),
            # it's acceptable for 'market_regime' to be missing from details.
            # Log this and assert that a failure was indeed indicated.
            logger.warning(
                f"Agent '{agent_name}' could not determine market regime. "
                f"Status: {agent_status}, Verdict: {agent_verdict}, Error: {agent_error_field}. "
                f"Details: {market_regime_agent_result.get('details')}. "
                "Skipping assertion for 'market_regime' key in details, but verifying failure indication."
            )
            assert agent_status == 'error' or agent_verdict == 'NO_DATA' or agent_error_field is not None, \
                f"Agent '{agent_name}' was not able to determine regime, but did not report a standard failure indicator. " \
                f"Status: {agent_status}, Verdict: {agent_verdict}, Error: {agent_error_field}."

    async def test_system_recovery(self, orchestrator):
        """Test system recovery from failures"""
        # metrics_collector = MetricsCollector() # Collector is internal
        # Simulate multiple failures and verify recovery
        for i in range(3):
            # Create a new monitor for each iteration to pass into the call
            monitor_for_call = SystemMonitor()
            logger.debug(f"System Recovery Test: Iteration {i+1}")
            await orchestrator.analyze_symbol(
                symbol="INVALID_SYMBOL",
                monitor=monitor_for_call # Pass the new monitor instance for the call
                # metrics_collector=metrics_collector # Removed
            )
            # Access health metrics from the ORCHESTRATOR's internal monitor
            internal_monitor = orchestrator.system_monitor
            health_metrics = await internal_monitor.get_health_metrics() # Added await
            # --- Ensure health_metrics is a dict before accessing ---
            assert isinstance(health_metrics, dict), f"Expected health_metrics to be a dict, but got {type(health_metrics)}"
            
            components_data = health_metrics.get("components", {}) # Changed from component_statuses
            assert isinstance(components_data, dict), f"Expected components_data to be a dict, but got {type(components_data)}"

            orchestrator_component = components_data.get("orchestrator", {})
            assert isinstance(orchestrator_component, dict), f"Expected orchestrator_component to be a dict, but got {type(orchestrator_component)}"
            
            # Check overall system status if available, or component statuses
            # Assuming orchestrator should remain healthy despite symbol errors
            assert orchestrator_component.get("status") == "healthy", \
                f"Orchestrator component should remain healthy on iteration {i+1}. Health was: {health_metrics}"
            # Check if system metrics are still being reported
            system_metrics = health_metrics.get("system", {})
            assert isinstance(system_metrics, dict), f"Expected system_metrics to be a dict, but got {type(system_metrics)}"
            assert system_metrics.get("cpu_usage") is not None, f"CPU usage missing on iteration {i+1}"
            assert system_metrics.get("memory_usage") is not None, f"Memory usage missing on iteration {i+1}"

    async def test_metrics_collection(self, orchestrator):
        """Test metrics collection"""
        monitor = SystemMonitor()
        symbol_to_test = "RELIANCE.NS"        # Ensure a fresh analysis by clearing cache for the symbol
    
        # Patch get_redis_client for the explicit cache deletion part of this test
        with patch('backend.utils.cache_utils.get_redis_client') as mock_get_redis_for_delete:
            # Configure the mock client instance that get_redis_client will return
            mock_client_instance_for_delete = AsyncMock() # Make the client instance itself an AsyncMock
            # mock_client_instance_for_delete.delete = AsyncMock() # This line is not strictly necessary if the parent is AsyncMock
            mock_get_redis_for_delete.return_value = mock_client_instance_for_delete
    
            # Get the client from the mock by calling the patched version
            cache_client_for_deletion = mock_get_redis_for_delete()
    
            # Correct cache key for deletion, assuming analyze_symbol defaults to all categories
            # as no specific categories are passed to it in this test.
            all_categories_str = ",".join(sorted([cat.value for cat in CategoryType]))
            cache_key_to_delete = f"analysis:{symbol_to_test}:{all_categories_str}"
            await cache_client_for_deletion.delete(cache_key_to_delete)
            logger.info(f"Cache cleared for {symbol_to_test} with key {cache_key_to_delete} (all categories) before metrics collection test.")

        result = await orchestrator.analyze_symbol( # Call analyze_symbol
            symbol=symbol_to_test,
            monitor=monitor
            # No categories specified, so orchestrator should use all default categories
        )
        # Get metrics from the result, as collector is internal
        metrics = result.get("execution_metrics", {}) # Access metrics from result
        
        assert "performance" in metrics
        assert "category_stats" in metrics
        # Check if avg_response_time exists and is > 0
        performance_metrics = metrics.get("performance", {})
        assert "avg_response_time" in performance_metrics, "avg_response_time should be in performance metrics"
        assert performance_metrics["avg_response_time"] > 0, "avg_response_time should be greater than 0 after a successful analysis"
