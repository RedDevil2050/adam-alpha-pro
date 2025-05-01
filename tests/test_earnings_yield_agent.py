import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest.mock import AsyncMock, patch
from backend.agents.valuation.earnings_yield_agent import run as ey_run

agent_name = "earnings_yield_agent"

@pytest.mark.asyncio
# Patch dependencies (innermost first)
@patch('backend.agents.decorators.get_tracker') # Decorator dependency
@patch('backend.agents.decorators.get_redis_client') # Decorator dependency
@patch('backend.agents.valuation.earnings_yield_agent.fetch_price_point')
@patch('backend.agents.valuation.earnings_yield_agent.fetch_company_info')
async def test_earnings_yield_agent_attractive(
    mock_fetch_info, 
    mock_fetch_price, 
    mock_get_redis, 
    mock_get_tracker
):
    # --- Mock Configuration ---
    symbol = "TEST_SYMBOL"
    current_price = 100.0
    eps = 10.0 # Results in 10% yield (10/100 * 100)

    # 1. Mock fetch_company_info (provide EPS)
    mock_fetch_info.return_value = {"EPS": str(eps)}

    # 2. Mock fetch_price_point
    # Assuming fetch_price_point returns {'price': ...}
    mock_fetch_price.return_value = {"price": current_price}

    # 3. Mock Redis
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get.return_value = None # Cache miss
    mock_redis_instance.set = AsyncMock()
    mock_get_redis.return_value = mock_redis_instance

    # 4. Mock Tracker
    mock_tracker_instance = AsyncMock()
    mock_tracker_instance.update_agent_status = AsyncMock()
    mock_get_tracker.return_value = mock_tracker_instance

    # --- Expected Calculations ---
    expected_yield = (eps / current_price) * 100 # 10.0
    # Assuming high_threshold = 8.0 in agent
    expected_verdict = "ATTRACTIVE"
    expected_confidence = 0.8

    # --- Run Agent ---
    result = await ey_run(symbol)

    # --- Assertions ---
    assert result['symbol'] == symbol
    assert result['agent_name'] == agent_name
    assert result['verdict'] == expected_verdict
    assert result['confidence'] == pytest.approx(expected_confidence)
    assert result['value'] == pytest.approx(expected_yield) # Value is the yield %
    assert result.get('error') is None

    # Check details
    assert 'details' in result
    details = result['details']
    assert details['earnings_yield_percent'] == pytest.approx(expected_yield)
    assert details['current_price'] == pytest.approx(current_price)
    assert details['eps'] == pytest.approx(eps)
    assert details['eps_source'] == "company_info"

    # --- Verify Mocks ---
    mock_fetch_info.assert_awaited_once_with(symbol)
    mock_fetch_price.assert_awaited_once_with(symbol)
    mock_get_redis.assert_awaited_once()
    mock_redis_instance.get.assert_awaited_once()
    mock_redis_instance.set.assert_awaited_once() # Should cache on success
    mock_get_tracker.assert_called_once() # Check if tracker was fetched
    mock_tracker_instance.update_agent_status.assert_awaited_once() # Check status update

# Removed old test function