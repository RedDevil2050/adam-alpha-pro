import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest.mock import AsyncMock, patch
from backend.agents.valuation.eps_agent import run as eps_run

agent_name = "eps_agent"

@pytest.mark.asyncio
# Patch dependencies (innermost first)
@patch('backend.agents.decorators.get_tracker') # Decorator dependency
@patch('backend.agents.decorators.get_redis_client') # Decorator dependency
@patch('backend.agents.valuation.eps_agent.fetch_company_info')
async def test_eps_agent_positive(
    mock_fetch_info, 
    mock_get_redis, 
    mock_get_tracker
):
    # --- Mock Configuration ---
    symbol = "TEST_SYMBOL"
    eps_value = 5.50

    # 1. Mock fetch_company_info (provide positive EPS)
    mock_fetch_info.return_value = {"EPS": str(eps_value)}

    # 2. Mock Redis
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get.return_value = None # Cache miss
    mock_redis_instance.set = AsyncMock()
    mock_get_redis.return_value = mock_redis_instance

    # 3. Mock Tracker
    mock_tracker_instance = AsyncMock()
    mock_tracker_instance.update_agent_status = AsyncMock()
    mock_get_tracker.return_value = mock_tracker_instance

    # --- Expected Results ---
    expected_verdict = "POSITIVE_EPS"
    expected_confidence = 0.95

    # --- Run Agent ---
    result = await eps_run(symbol)

    # --- Assertions ---
    assert result['symbol'] == symbol
    assert result['agent_name'] == agent_name
    assert result['verdict'] == expected_verdict
    assert result['confidence'] == pytest.approx(expected_confidence)
    assert result['value'] == pytest.approx(eps_value) # Value is the EPS
    assert result.get('error') is None

    # Check details
    assert 'details' in result
    details = result['details']
    assert details['eps'] == pytest.approx(eps_value)
    assert details['data_source'] == "alpha_vantage_overview"

    # --- Verify Mocks ---
    mock_fetch_info.assert_awaited_once_with(symbol)
    mock_get_redis.assert_awaited_once()
    mock_redis_instance.get.assert_awaited_once()
    mock_redis_instance.set.assert_awaited_once() # Should cache on success
    mock_get_tracker.assert_called_once() # Check if tracker was fetched
    mock_tracker_instance.update_agent_status.assert_awaited_once() # Check status update