import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import pandas as pd
from unittest.mock import AsyncMock, patch
from backend.agents.technical.moving_average_agent import run as ma_run
import datetime
import numpy as np # Import numpy if not already present

@pytest.mark.asyncio
@patch('backend.agents.decorators.get_redis_client')  # Patch redis client used by decorator
@patch('backend.agents.technical.moving_average_agent.fetch_ohlcv_series') # Patch fetch_ohlcv_series where it's used
async def test_moving_average_agent(mock_fetch, mock_get_redis, monkeypatch): # Mocks are passed in reverse order of decorators
    # Create realistic OHLCV data with uptrend (ensure enough data for window + 1)
    window = 20
    num_days = window + 10 # Need at least window + 1 for MA calculation
    dates = pd.to_datetime([datetime.date(2025, 4, 30) - datetime.timedelta(days=x) for x in range(num_days - 1, -1, -1)])
    prices_df = pd.DataFrame({
        'high': np.linspace(101, 101 + num_days, num_days),
        'low': np.linspace(99, 99 + num_days, num_days),
        'close': np.linspace(100, 100 + num_days, num_days),  # Increasing trend
        'open': np.linspace(100, 100 + num_days, num_days),
        'volume': [1000] * num_days
    }, index=dates)

    # Configure the mock fetch_ohlcv_series passed by @patch
    mock_fetch.return_value = prices_df

    # Set up Redis mock instance and return value correctly
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get = AsyncMock(return_value=None)  # Simulate cache miss
    mock_redis_instance.set = AsyncMock()
    mock_get_redis.return_value = mock_redis_instance # Make the patched function return our mock instance

    # Mock tracker (optional, ensure path is correct)
    # Using try-except for robustness if tracker path changes
    try:
        mock_tracker_update = AsyncMock()
        # Assuming tracker is imported/used within the decorator now
        monkeypatch.setattr('backend.monitor.tracker.AgentTracker.update_agent_status', mock_tracker_update)
    except (AttributeError, ImportError):
        print("Could not patch tracker.update_agent_status, continuing...")


    # Run the agent with a specific window and agent_outputs
    res = await ma_run('TCS', window=window, agent_outputs={}) # Pass agent_outputs

    # Verify mocks were called correctly
    mock_fetch.assert_awaited_once() # Use assert_awaited_once for async mocks
    # Check arguments passed to mock_fetch
    call_args, call_kwargs = mock_fetch.call_args
    assert call_kwargs.get('symbol') == 'TCS'
    assert isinstance(call_kwargs.get('start_date'), datetime.date)
    assert isinstance(call_kwargs.get('end_date'), datetime.date)
    assert call_kwargs.get('interval') == '1d'

    # Verify Redis operations were called
    mock_redis_instance.get.assert_awaited_once()
    # Set should be called if the result is valid (not NO_DATA/ERROR)
    if res.get('verdict') not in ['NO_DATA', 'ERROR', None]:
        mock_redis_instance.set.assert_awaited_once()
    else:
        mock_redis_instance.set.assert_not_awaited()


    # Verify results
    assert 'verdict' in res
    assert res['verdict'] == 'BUY'  # Based on increasing price data
    assert 'confidence' in res
    assert res['confidence'] > 0  # Should have positive confidence
    assert 'value' in res  # Slope percentage
    assert res['value'] > 0  # Slope should be positive
    assert 'details' in res
    assert 'ma_last' in res['details']
    assert 'ma_prev' in res['details']
    assert 'slope_pct' in res['details']
    assert res.get('error') is None # Check for errors