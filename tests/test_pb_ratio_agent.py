import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import pandas as pd
import numpy as np
from unittest.mock import AsyncMock, patch, MagicMock # Added MagicMock
from backend.agents.valuation.pb_ratio_agent import run as pb_run
from backend.config.settings import get_settings # Import settings
from datetime import datetime, timedelta

agent_name = "pb_ratio_agent"

@pytest.mark.asyncio
# Patch in reverse order of execution (innermost first)
@patch('backend.agents.decorators.get_tracker') # Patch tracker
@patch('backend.agents.decorators.get_redis_client') # Corrected redis patch target
# Correct patch targets to where functions are *used* in the agent module
@patch('backend.agents.valuation.pb_ratio_agent.fetch_historical_price_series') 
@patch('backend.agents.valuation.pb_ratio_agent.fetch_latest_bvps')
@patch('backend.agents.valuation.pb_ratio_agent.fetch_price_point')
# Correct the patch target to where 'stats' is used in the agent module
@patch('scipy.stats') # Target the actual library
async def test_pb_ratio_agent_undervalued(
    mock_stats, # Mock for the imported stats name
    mock_fetch_price, 
    mock_fetch_bvps, 
    mock_fetch_hist, 
    mock_get_redis, 
    mock_get_tracker, # Added tracker mock
    monkeypatch
):
    # --- Mock Configuration ---
    settings = get_settings()
    pb_settings = settings.agent_settings.pb_ratio
    years = pb_settings.HISTORICAL_YEARS
    num_days = years * 365 + 1 # Ensure enough data

    # --- Mock Data ---
    # 1. Mock Current Price
    mock_fetch_price.return_value = {"latestPrice": 100.0}
    
    # 2. Mock Latest BVPS
    mock_fetch_bvps.return_value = {"bookValuePerShare": 50.0}
    # Expected Current P/B = 100 / 50 = 2.0

    # 3. Mock Historical Prices (Create a series where P/B=2.0 is low)
    # Let historical P/B range mostly from 2.5 to 3.5
    # Historical prices = historical P/B * current BVPS
    hist_pb_values = np.linspace(2.5, 3.5, num_days)
    hist_prices = hist_pb_values * 50.0 # Use the mocked BVPS
    dates = pd.to_datetime([datetime.now() - timedelta(days=x) for x in range(num_days - 1, -1, -1)])
    mock_hist_series = pd.Series(hist_prices, index=dates, name="close")
    mock_fetch_hist.return_value = mock_hist_series

    # 4. Mock Redis
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get.return_value = None # Cache miss
    mock_redis_instance.set = AsyncMock()
    # Configure the mock for get_redis_client to return the instance correctly
    async def fake_get_redis():
        return mock_redis_instance
    mock_get_redis.side_effect = fake_get_redis

    # 5. Mock percentileofscore on the mocked stats module
    # This should trigger the UNDERVALUED_REL_HIST verdict
    mock_stats.percentileofscore.return_value = 15.0 # Assuming PERCENTILE_UNDERVALUED is e.g., 20

    # 6. Mock Tracker
    mock_tracker_instance = MagicMock()
    mock_tracker_instance.update_agent_status = AsyncMock()
    mock_get_tracker.return_value = mock_tracker_instance

    # --- Run Agent ---
    result = await pb_run('TEST_SYMBOL')

    # --- Assertions ---
    assert result['symbol'] == 'TEST_SYMBOL'
    assert result['agent_name'] == agent_name
    assert result['value'] == pytest.approx(2.0) # Current P/B
    
    # Check verdict based on mocked percentile (15) and default settings (20)
    assert result['verdict'] == 'UNDERVALUED_REL_HIST' 
    assert 'confidence' in result
    assert 0.6 <= result['confidence'] <= 0.9 # Confidence calculation for undervalued
    assert result.get('error') is None

    # Check details
    assert 'details' in result
    details = result['details']
    assert details['current_pb_ratio'] == pytest.approx(2.0)
    assert details['current_bvps'] == 50.0
    assert details['current_price'] == 100.0
    # Assert percentile rank based on the mocked return value
    assert details['percentile_rank'] == pytest.approx(15.0) # Corrected assertion
    assert details['historical_mean_pb'] == pytest.approx(3.0) # Mean of linspace(2.5, 3.5)
    assert details['z_score'] < 0 # Current P/B is below the mean
    assert details['data_source'] == "calculated_fundamental + historical_prices"

    # --- Verify Mocks ---
    mock_fetch_price.assert_awaited_once_with('TEST_SYMBOL')
    mock_fetch_bvps.assert_awaited_once_with('TEST_SYMBOL')
    mock_fetch_hist.assert_awaited_once()
    # Check hist call args more precisely if needed
    hist_call_args, hist_call_kwargs = mock_fetch_hist.call_args
    assert hist_call_args[0] == 'TEST_SYMBOL'
    assert 'start_date' in hist_call_kwargs
    assert 'end_date' in hist_call_kwargs

    mock_get_redis.assert_awaited_once()
    mock_redis_instance.get.assert_awaited_once()
    mock_redis_instance.set.assert_awaited_once() # Should cache on success
    mock_stats.percentileofscore.assert_called_once() # Ensure scipy function was called

    # Verify tracker update was called
    mock_get_tracker.assert_called_once()
    mock_tracker_instance.update_agent_status.assert_awaited_once()