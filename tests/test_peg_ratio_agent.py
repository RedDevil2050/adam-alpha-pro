import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import asyncio
from unittest.mock import AsyncMock, patch # Import AsyncMock and patch
from backend.agents.valuation.peg_ratio_agent import run as peg_run

agent_name = "peg_ratio_agent"

@pytest.mark.asyncio
# Patch dependencies (innermost first)
@patch('backend.agents.decorators.get_tracker') # Decorator dependency
@patch('backend.agents.decorators.get_redis_client') # Decorator dependency
@patch('backend.agents.valuation.peg_ratio_agent.fetch_company_info')
async def test_peg_ratio_agent_fair_value(
    mock_fetch_info, 
    mock_get_redis, 
    mock_get_tracker
):
    # --- Mock Configuration ---
    symbol = 'TEST'
    mock_pe_ratio = 10.0
    mock_growth_rate = 5.0 # PEG = 10 / 5 = 2.0

    # 1. Mock agent_outputs (providing PE ratio)
    agent_outputs = {
        symbol: {
            'pe_ratio_agent': {
                'value': mock_pe_ratio, 
                'verdict': 'SOME_PE_VERDICT' # Actual verdict doesn't matter here
            }
        }
    }

    # 2. Mock fetch_company_info (providing growth rate)
    # Use a key the agent looks for, e.g., 'EPSGrowthRate5Years'
    mock_fetch_info.return_value = {
        "EPSGrowthRate5Years": str(mock_growth_rate) # Simulate string value
    }

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
    expected_peg = mock_pe_ratio / mock_growth_rate # 2.0
    expected_verdict = "FAIR_VALUE" # Based on 1 <= PEG <= 2

    # --- Run Agent ---
    # Pass agent_outputs as the second argument
    result = await peg_run(symbol, agent_outputs)

    # --- Assertions ---
    assert result['symbol'] == symbol
    assert result['agent_name'] == agent_name
    # Check the calculated PEG ratio in 'value'
    assert result['value'] == pytest.approx(expected_peg)
    # Check the verdict based on the agent's logic
    assert result['verdict'] == expected_verdict 
    assert 'confidence' in result
    assert result.get('error') is None

    # Check details
    assert 'details' in result
    details = result['details']
    assert details['peg_ratio'] == pytest.approx(expected_peg)
    assert details['pe_ratio'] == pytest.approx(mock_pe_ratio)
    assert details['growth_rate_pct'] == pytest.approx(mock_growth_rate)
    assert details['pe_source'] == "pe_ratio_agent"

    # --- Verify Mocks ---
    mock_fetch_info.assert_awaited_once_with(symbol)
    mock_get_redis.assert_awaited_once()
    mock_redis_instance.get.assert_awaited_once()
    mock_redis_instance.set.assert_awaited_once() # Should cache on success
    mock_get_tracker.assert_called_once() # Check if tracker was fetched
    mock_tracker_instance.update_agent_status.assert_awaited_once() # Check status update