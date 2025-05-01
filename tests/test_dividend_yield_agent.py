import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest.mock import AsyncMock, patch
# Import the agent's run function
from backend.agents.valuation.dividend_yield_agent import run as dy_run 

agent_name = "dividend_yield_agent"

@pytest.mark.asyncio
# Patch dependencies used by the agent (innermost first)
@patch('backend.agents.decorators.get_tracker') # Decorator dependency
@patch('backend.agents.decorators.get_redis_client') # Decorator dependency
@patch('backend.agents.valuation.dividend_yield_agent.fetch_price_point')
@patch('backend.agents.valuation.dividend_yield_agent.fetch_company_info')
async def test_dividend_yield_agent(
    mock_fetch_info, 
    mock_fetch_price, 
    mock_get_redis, 
    mock_get_tracker # Add tracker mock parameter
):
    # --- Mock Configuration ---
    symbol = "TEST"
    mock_price = 100.0
    mock_yield_decimal = 0.04 # 4%
    mock_dps = 4.0 # Price * Yield

    # 1. Mock fetch_company_info (provide yield and/or DPS)
    # Simulate data source providing yield as a decimal string
    mock_fetch_info.return_value = {
        "DividendYield": str(mock_yield_decimal), 
        "DividendPerShare": str(mock_dps)
    }

    # 2. Mock fetch_price_point
    # Assuming fetch_price_point returns {'latestPrice': ...}
    mock_fetch_price.return_value = {"latestPrice": mock_price}

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
    expected_yield_percent = mock_yield_decimal * 100 # 4.0
    # Assuming THRESHOLD_MODERATE < 4.0 < THRESHOLD_ATTRACTIVE
    expected_verdict = "MODERATE_YIELD" # Adjust based on actual thresholds if needed

    # --- Run Agent ---
    result = await dy_run(symbol)

    # --- Assertions ---
    assert result['symbol'] == symbol
    assert result['agent_name'] == agent_name
    # Check the 'value' key for the yield percentage
    assert result['value'] == pytest.approx(expected_yield_percent) 
    assert result['verdict'] == expected_verdict
    assert 'confidence' in result
    assert isinstance(result['confidence'], float)
    assert 0 <= result['confidence'] <= 1.0
    assert result.get('error') is None

    # Check details
    assert 'details' in result
    details = result['details']
    assert details['yield_percent'] == pytest.approx(expected_yield_percent)
    assert details['current_price'] == pytest.approx(mock_price)
    assert details['annual_dividend_per_share'] == pytest.approx(mock_dps)
    assert details['data_source'] == "company_info + price_point"

    # --- Verify Mocks ---
    mock_fetch_info.assert_awaited_once_with(symbol)
    mock_fetch_price.assert_awaited_once_with(symbol)
    mock_get_redis.assert_awaited_once()
    mock_redis_instance.get.assert_awaited_once()
    mock_redis_instance.set.assert_awaited_once() # Should cache on success
    mock_get_tracker.assert_called_once() # Check if tracker was fetched
    mock_tracker_instance.update_agent_status.assert_awaited_once() # Check status update