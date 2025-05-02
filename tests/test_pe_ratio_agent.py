import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import pandas as pd # Import pandas
import numpy as np # Import numpy
from unittest.mock import AsyncMock, patch
from backend.agents.valuation.pe_ratio_agent import run as pe_run
from datetime import datetime, timedelta # Import datetime

@pytest.mark.asyncio
@patch('backend.agents.decorators.get_tracker') # Add tracker patch
@patch('backend.agents.decorators.get_redis_client')
# Add patches for the actual functions used by the agent
@patch('backend.agents.valuation.pe_ratio_agent.fetch_historical_price_series')
@patch('backend.agents.valuation.pe_ratio_agent.fetch_latest_eps')
@patch('backend.agents.valuation.pe_ratio_agent.fetch_price_point')
async def test_pe_ratio_agent(
    mock_fetch_price, # Mock for fetch_price_point
    mock_fetch_eps,   # Mock for fetch_latest_eps
    mock_fetch_hist,  # Mock for fetch_historical_price_series
    mock_get_redis,
    mock_get_tracker, # Add tracker mock argument
    monkeypatch # Keep monkeypatch if needed for other things, otherwise remove
):
    # --- Mock Configuration ---
    symbol = 'TEST_PE'
    current_price = 200.0
    current_eps = 10.0
    expected_pe = 20.0
    years = 3 # Example: Use 3 years of historical data
    num_days = years * 365 + 1

    # 1. Mock fetch_price_point
    mock_fetch_price.return_value = {"latestPrice": current_price}

    # 2. Mock fetch_latest_eps
    mock_fetch_eps.return_value = {"eps": current_eps}

    # 3. Mock fetch_historical_price_series (e.g., prices implying PE around 25)
    hist_pe_values = np.linspace(22, 28, num_days)
    hist_prices = hist_pe_values * current_eps # Prices = PE * EPS
    dates = pd.to_datetime([datetime.now() - timedelta(days=x) for x in range(num_days - 1, -1, -1)])
    mock_hist_series = pd.Series(hist_prices, index=dates, name="close")
    mock_fetch_hist.return_value = mock_hist_series

    # 4. Mock Redis
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get = AsyncMock(return_value=None)  # Simulate cache miss
    mock_redis_instance.set = AsyncMock()
    async def fake_get_redis(): return mock_redis_instance
    mock_get_redis.side_effect = fake_get_redis

    # 5. Mock Tracker
    mock_tracker_instance = AsyncMock()
    mock_tracker_instance.update_agent_status = AsyncMock()
    mock_get_tracker.return_value = mock_tracker_instance

    # --- Remove incorrect monkeypatch ---
    # monkeypatch.setattr('backend.utils.data_provider.fetch_financial_data', mock_fetch_financial_data)

    # --- Run the agent ---
    result = await pe_run(symbol)

    # --- Verify Redis operations ---
    mock_get_redis.assert_awaited_once()
    mock_redis_instance.get.assert_awaited_once()
    # Assert set is called because data is valid
    mock_redis_instance.set.assert_awaited_once()

    # --- Verify Tracker --- 
    mock_get_tracker.assert_called_once()
    mock_tracker_instance.update_agent_status.assert_awaited_once()

    # --- Verify Data Fetch Mocks ---
    mock_fetch_price.assert_awaited_once_with(symbol)
    mock_fetch_eps.assert_awaited_once_with(symbol)
    mock_fetch_hist.assert_awaited_once()
    hist_call_args, hist_call_kwargs = mock_fetch_hist.call_args
    assert hist_call_args[0] == symbol
    assert 'start_date' in hist_call_kwargs
    assert 'end_date' in hist_call_kwargs

    # --- Verify results ---
    assert result['symbol'] == symbol
    assert result['agent_name'] == 'pe_ratio_agent'
    assert result['value'] == pytest.approx(expected_pe) # Current PE
    # Based on mock data (current PE=20, hist PE mean=25), expect UNDERVALUED
    assert result['verdict'] == 'UNDERVALUED_REL_HIST'
    assert 'confidence' in result
    assert 0.0 <= result['confidence'] <= 1.0
    assert result.get('error') is None
    assert 'details' in result
    assert result['details']['current_pe_ratio'] == pytest.approx(expected_pe)
    assert result['details']['current_eps'] == pytest.approx(current_eps)
    assert result['details']['current_price'] == pytest.approx(current_price)
    assert 'percentile_rank' in result['details']
    # Expect low percentile rank because 20 is below the 22-28 range
    assert result['details']['percentile_rank'] < 20 # Adjust threshold based on agent settings if needed