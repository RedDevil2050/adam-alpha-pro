import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock # Import patch and MagicMock
from backend.agents.valuation.dcf_agent import run as dcf_run # Use alias
from backend.config.settings import get_settings # Import settings

agent_name = "dcf_agent"

@pytest.mark.asyncio
# Patch dependencies (innermost first)
@patch('backend.agents.decorators.get_tracker') # Decorator dependency
@patch('backend.agents.decorators.get_redis_client') # Decorator dependency
@patch('backend.agents.valuation.dcf_agent.simulate_dcf')
@patch('backend.agents.valuation.dcf_agent.fetch_alpha_vantage')
@patch('backend.agents.valuation.dcf_agent.fetch_price_point')
async def test_dcf_agent_buy_scenario(
    mock_fetch_price, 
    mock_fetch_av, 
    mock_simulate_dcf, 
    mock_get_redis, 
    mock_get_tracker, 
    monkeypatch # Use monkeypatch if needed for settings or other direct patches
):
    # --- Mock Configuration ---
    symbol = "TEST_SYMBOL"
    current_price = 100.0
    simulated_intrinsic_value = 150.0 # Value returned by each simulation run
    n_simulations = 1000 # Match the agent's simulation count

    # 1. Mock fetch_price_point
    mock_fetch_price.return_value = {"latestPrice": current_price}

    # 2. Mock fetch_alpha_vantage (provide EPS and Beta)
    mock_fetch_av.return_value = {"EPS": "10.0", "Beta": "1.1"}
    base_eps = 10.0
    beta = 1.1

    # 3. Mock simulate_dcf to return a consistent high value
    # This makes the mean value predictable (it will be simulated_intrinsic_value)
    mock_simulate_dcf.return_value = simulated_intrinsic_value

    # 4. Mock Redis
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get.return_value = None # Cache miss
    mock_redis_instance.set = AsyncMock()
    mock_get_redis.return_value = mock_redis_instance

    # 5. Mock Tracker
    mock_tracker_instance = AsyncMock()
    mock_tracker_instance.update_agent_status = AsyncMock()
    mock_get_tracker.return_value = mock_tracker_instance

    # --- Expected Calculations ---
    # Margin of Safety = (150 - 100) / 100 * 100 = 50.0%
    # Since MoS > 30%, verdict should be STRONG_BUY, base_confidence = 0.9
    # Since simulate_dcf always returns the same value, std_dev = 0, relative_std_dev = 0
    # Uncertainty penalty = 0
    # Final confidence = 0.9 * (1 - 0) = 0.9
    expected_verdict = "STRONG_BUY"
    expected_confidence = 0.9
    expected_value = simulated_intrinsic_value # Mean value

    # --- Run Agent ---
    # No need for dummy_outputs if mocking AV to provide EPS
    result = await dcf_run(symbol, agent_outputs={}) 

    # --- Assertions ---
    assert result['symbol'] == symbol
    assert result['agent_name'] == agent_name
    assert result['verdict'] == expected_verdict
    assert result['confidence'] == pytest.approx(expected_confidence)
    assert result['value'] == pytest.approx(expected_value)
    assert result.get('error') is None

    # Check details
    assert 'details' in result
    details = result['details']
    assert details['current_price'] == pytest.approx(current_price)
    assert details['intrinsic_value_mean'] == pytest.approx(expected_value)
    assert details['margin_of_safety_percent'] == pytest.approx(50.0)
    assert 'simulation_summary' in details
    assert details['simulation_summary']['count'] == n_simulations
    assert details['simulation_summary']['std_dev'] == pytest.approx(0.0)
    assert details['simulation_summary']['relative_std_dev'] == pytest.approx(0.0)
    assert details['simulation_summary']['5th_percentile'] == pytest.approx(expected_value)
    assert details['simulation_summary']['95th_percentile'] == pytest.approx(expected_value)
    assert 'inputs' in details
    assert details['inputs']['base_eps'] == pytest.approx(base_eps)
    assert details['inputs']['eps_source'] == "alpha_vantage_overview"
    assert details['inputs']['beta'] == pytest.approx(beta)
    assert details['inputs']['beta_source'] == "alpha_vantage_overview"

    # --- Verify Mocks ---
    mock_fetch_price.assert_awaited_once_with(symbol)
    mock_fetch_av.assert_awaited_once_with(symbol, "overview")
    # Check simulate_dcf was called n_simulations times
    assert mock_simulate_dcf.call_count == n_simulations 
    mock_get_redis.assert_awaited_once()
    mock_redis_instance.get.assert_awaited_once()
    mock_redis_instance.set.assert_awaited_once() # Should cache on success
    mock_get_tracker.assert_called_once() # Check if tracker was fetched
    # Check if tracker status was updated (decorator handles this)
    mock_tracker_instance.update_agent_status.assert_awaited_once()
