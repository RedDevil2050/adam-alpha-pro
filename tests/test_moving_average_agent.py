import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import pandas as pd
from unittest.mock import AsyncMock, patch, MagicMock
from backend.agents.technical.moving_average_agent import run as ma_run
import datetime
import numpy as np # Import numpy if not already present

@pytest.mark.asyncio
@patch('backend.agents.decorators.get_tracker') # Outermost patch 
@patch('backend.agents.decorators.get_redis_client', new_callable=AsyncMock)
@patch('backend.agents.technical.moving_average_agent.fetch_ohlcv_series', new_callable=AsyncMock)
# Patch date and timedelta directly in the agent's module
@patch('backend.agents.technical.moving_average_agent.date') 
@patch('backend.agents.technical.moving_average_agent.timedelta')
async def test_moving_average_agent(
    mock_timedelta_agent, # Corresponds to moving_average_agent.timedelta
    mock_date_agent,      # Corresponds to moving_average_agent.date
    mock_fetch_ohlcv,    # Corresponds to moving_average_agent.fetch_ohlcv_series
    mock_decorator_redis,    # Corresponds to decorators.get_redis_client
    mock_decorator_tracker   # Corresponds to decorators.get_tracker
):
    # --- Mock Agent Settings ---
    # mock_agent_settings.LOOKBACK_DAYS_MULTIPLIER = 2 # Example: Use a different multiplier
    # mock_agent_settings.ADDITIONAL_LOOKBACK_DAYS = 30 # Example: Use different additional days

    # --- Mock datetime ---
    real_datetime_date_class = datetime.date
    real_datetime_timedelta_class = datetime.timedelta
    # Fixed date for reproducible test runs
    mock_today_date_object = real_datetime_date_class(2025, 7, 20)

    mock_date_agent.today.return_value = mock_today_date_object
    # Make the mocked timedelta behave like the real one for calculations
    mock_timedelta_agent.side_effect = lambda days: real_datetime_timedelta_class(days=days)

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
    mock_decorator_redis.return_value = mock_redis_instance

    # Mock tracker instance returned by the decorator's get_tracker
    mock_tracker_instance = MagicMock() # Use MagicMock for synchronous get_tracker
    mock_tracker_instance.update_agent_status = AsyncMock() # update_agent_status is async
    mock_decorator_tracker.return_value = mock_tracker_instance

    # Run the agent with a specific window and agent_outputs
    res = await ma_run('TCS', window=window, agent_outputs={}) # Pass agent_outputs

    # Verify mocks were called correctly
    mock_fetch_ohlcv.assert_awaited_once() # Use assert_awaited_once for async mocks
    
    # Calculate expected dates for fetch_ohlcv_series call
    # The agent calculates: required_data_days = max(window, atr_period, volume_avg_period, velocity_period) + slope_period + 60
    # Default values: atr_period=14, volume_avg_period=20, velocity_period=5, slope_period=1
    expected_lookback_days = max(window, 14, 20, 5) + 1 + 60  # = max(20,14,20,5) + 1 + 60 = 81
    expected_start_date = mock_today_date_object - real_datetime_timedelta_class(days=expected_lookback_days)
    expected_end_date = mock_today_date_object

    # Check arguments passed to mock_fetch_ohlcv
    call_args, call_kwargs = mock_fetch_ohlcv.call_args
    assert call_kwargs.get('symbol') == 'TCS'
    assert call_kwargs.get('start_date') == expected_start_date
    assert call_kwargs.get('end_date') == expected_end_date
    assert call_kwargs.get('interval') == '1d'

    # Verify Redis operations were called
    mock_decorator_redis.assert_awaited_once()
    
    # The decorator calls .get() for caching, but since this agent doesn't use AgentBase redis directly,
    # we only expect one call from the decorator
    assert mock_redis_instance.get.await_count == 1 # Only from decorator

    # Set should be called if the result is valid (not NO_DATA/ERROR)
    if res.get('verdict') not in ['NO_DATA', 'ERROR', None]:
        assert mock_redis_instance.set.await_count == 1 # Decorator handles caching the final result.
    else:
        mock_redis_instance.set.assert_not_awaited()

    # Verify tracker operations
    mock_decorator_tracker.assert_called_once()
    mock_tracker_instance.update_agent_status.assert_awaited_once()
    
    # Verify results
    assert 'verdict' in res
    assert res['verdict'] in ['UPTREND_ACCELERATING', 'UPTREND_STRONG_SLOPE', 'PRICE_ABOVE_MA_HOLD']  # Based on increasing price data
    assert 'confidence' in res
    assert res['confidence'] > 0  # Should have positive confidence
    assert 'value' in res  # Slope percentage
    assert res['value'] > 0  # Slope should be positive
    assert 'details' in res
    assert 'ma_value' in res['details']  # Correct key name
    assert 'ma_slope_pct' in res['details']
    assert res.get('error') is None # Check for errors