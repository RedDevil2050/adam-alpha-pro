import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import pandas as pd
from unittest.mock import AsyncMock, patch
from backend.agents.technical.moving_average_agent import run as ma_run
import datetime
import numpy as np # Import numpy if not already present

@pytest.mark.asyncio
@patch('backend.agents.decorators.get_redis_client', new_callable=AsyncMock)  # Patches redis client used by decorator
@patch('backend.agents.technical.moving_average_agent.fetch_ohlcv_series', new_callable=AsyncMock) # Patches fetch_ohlcv_series where it's used in the agent
@patch('backend.agents.technical.moving_average_agent.get_redis_client', new_callable=AsyncMock) # Patches redis client used directly by the agent
async def test_moving_average_agent(mock_agent_get_redis_client, mock_fetch_ohlcv, mock_decorator_get_redis_client, monkeypatch): # Mocks are passed in reverse order of decorators: innermost to outermost
    # mock_agent_get_redis_client is for backend.agents.technical.moving_average_agent.get_redis_client
    # mock_fetch_ohlcv is for backend.agents.technical.moving_average_agent.fetch_ohlcv_series
    # mock_decorator_get_redis_client is for backend.agents.decorators.get_redis_client

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
    mock_fetch_ohlcv.return_value = prices_df

    # Set up a shared Redis mock instance
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get = AsyncMock(return_value=None)  # Simulate cache miss
    mock_redis_instance.set = AsyncMock()
    
    # Configure the decorator's get_redis_client mock to return the shared instance
    mock_decorator_get_redis_client.return_value = mock_redis_instance
    
    # Configure the agent's direct get_redis_client mock to return the shared instance
    mock_agent_get_redis_client.return_value = mock_redis_instance

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
    mock_fetch_ohlcv.assert_awaited_once() # Use assert_awaited_once for async mocks
    # Check arguments passed to mock_fetch_ohlcv
    call_args, call_kwargs = mock_fetch_ohlcv.call_args
    assert call_kwargs.get('symbol') == 'TCS'
    assert isinstance(call_kwargs.get('start_date'), datetime.date)
    assert isinstance(call_kwargs.get('end_date'), datetime.date)
    assert call_kwargs.get('interval') == '1d'

    # Verify Redis operations were called
    mock_decorator_get_redis_client.assert_awaited_once() # mock_decorator_get_redis_client is the factory for the decorator, should be awaited
    mock_agent_get_redis_client.assert_awaited_once() # mock_agent_get_redis_client is the factory for the agent, should be awaited
    
    # mock_redis_instance.get is called by the decorator and potentially by the agent if not using the decorator's result
    # If the agent uses its own redis_client instance to call .get(), and the decorator also calls .get(),
    # then two calls to .get() on potentially different instances (if not sharing mock_redis_instance) or the same one are expected.
    # Given the setup, both patched get_redis_client return the *same* mock_redis_instance.
    # The decorator calls .get() for caching.
    # The agent itself also calls get_redis_client() and then .get() on that client.
    # Thus, two calls to mock_redis_instance.get are expected.
    assert mock_redis_instance.get.await_count == 2

    # Set should be called if the result is valid (not NO_DATA/ERROR)
    if res.get('verdict') not in ['NO_DATA', 'ERROR', None]:
        assert mock_redis_instance.set.await_count == 2 # Expecting set to be called twice
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