import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import pandas as pd
import numpy as np
from unittest.mock import AsyncMock, patch, MagicMock
from backend.agents.technical.bollinger_agent import run as bollinger_run
import datetime

agent_name = "bollinger_agent"

@pytest.mark.asyncio
# Patch dependencies (innermost first)
@patch('backend.agents.technical.bollinger_agent.tracker.update')
@patch('backend.agents.technical.bollinger_agent.get_redis_client', new_callable=AsyncMock)
@patch('backend.agents.technical.bollinger_agent.fetch_ohlcv_series', new_callable=AsyncMock)
# Mock pandas rolling calculations
@patch('pandas.core.window.rolling.Rolling.mean') 
@patch('pandas.core.window.rolling.Rolling.std') 
async def test_bollinger_agent_buy_signal(
    mock_pd_std, mock_pd_mean, mock_fetch, mock_get_redis, mock_tracker_update
):
    # --- Mock Configuration ---
    window = 20
    num_std = 2.0

    # 1. Mock fetch_ohlcv_series
    # Create data where the last close is significantly lower
    dates = pd.to_datetime([datetime.date(2025, 4, 30) - datetime.timedelta(days=x) for x in range(window + 9, -1, -1)]) # window + 10 days
    close_prices = np.linspace(100, 110, window + 10) # General uptrend
    close_prices[-1] = 95 # Make the last close low
    data_df = pd.DataFrame({
        'high': close_prices + 1,
        'low': close_prices - 1,
        'close': close_prices,
        'open': close_prices,
        'volume': [1000] * (window + 10)
    }, index=dates)
    mock_fetch.return_value = data_df

    # 2. Mock Redis
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get.return_value = None # Cache miss
    mock_redis_instance.set = AsyncMock()
    mock_get_redis.return_value = mock_redis_instance

    # 3. Mock pandas rolling calculations
    # Mock MA calculation result
    mock_ma_series = MagicMock()
    mock_ma_series.iloc.__getitem__.return_value = 105.0 # Mock last MA value
    mock_pd_mean.return_value = mock_ma_series
    
    # Mock Std Dev calculation result
    mock_std_series = MagicMock()
    mock_std_series.iloc.__getitem__.return_value = 2.0 # Mock last Std Dev value
    mock_pd_std.return_value = mock_std_series

    # Expected bands based on mocks:
    # Upper = 105.0 + 2.0 * 2.0 = 109.0
    # Lower = 105.0 - 2.0 * 2.0 = 101.0
    # Last close = 95.0 (from data_df)
    # Since 95.0 < 101.0, expect BUY verdict

    # 4. Mock Tracker (already patched)
    mock_tracker_update.return_value = None

    # --- Run Agent ---
    res = await bollinger_run('TEST_SYMBOL', window=window, num_std=num_std)

    # --- Assertions ---
    assert res['symbol'] == 'TEST_SYMBOL'
    assert res['agent_name'] == agent_name
    assert res['verdict'] == 'BUY'
    assert res['confidence'] == 1.0 # Confidence is 1.0 for BUY
    assert res['value'] == 95.0 # Value is the last close price
    assert res.get('error') is None
    
    # Check details
    assert 'details' in res
    details = res['details']
    assert details['moving_average'] == pytest.approx(105.0)
    assert details['std_dev'] == pytest.approx(2.0)
    assert details['upper_band'] == pytest.approx(109.0)
    assert details['lower_band'] == pytest.approx(101.0)

    # --- Verify Mocks ---
    mock_fetch.assert_awaited_once()
    # Check fetch call args (might be simplified in agent, check agent code)
    # Assuming it calls fetch_ohlcv_series(symbol, ...)
    call_args, call_kwargs = mock_fetch.call_args
    assert call_args[0] == 'TEST_SYMBOL' 
    # Add more checks if fetch_ohlcv_series takes date ranges in this agent

    mock_get_redis.assert_awaited_once()
    mock_redis_instance.get.assert_awaited_once()
    mock_redis_instance.set.assert_awaited_once() # Should cache on success
    mock_tracker_update.assert_called_once_with("technical", agent_name, "implemented")
    
    # Verify pandas mocks
    assert mock_pd_mean.called
    mock_ma_series.iloc.__getitem__.assert_called_with(-1)
    assert mock_pd_std.called
    mock_std_series.iloc.__getitem__.assert_called_with(-1)
