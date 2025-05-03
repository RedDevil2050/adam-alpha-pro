import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import pandas as pd
import numpy as np
from unittest.mock import AsyncMock, patch, MagicMock
from backend.agents.technical.adx_agent import run as adx_run, agent_name # Import agent_name
import datetime

@pytest.mark.asyncio
# Patch dependencies in the correct order (innermost first)
@patch('backend.agents.technical.adx_agent.tracker.update')
@patch('backend.agents.technical.adx_agent.get_redis_client')
@patch('backend.agents.technical.adx_agent.fetch_ohlcv_series')
# Mock the final pandas calculation step to control the ADX value
@patch('pandas.core.window.rolling.Rolling.mean')
async def test_adx_agent_strong_trend(mock_pd_mean, mock_fetch, mock_get_redis, mock_tracker_update):
    # --- Mock Configuration ---
    symbol = 'TEST_SYMBOL'
    # 1. Mock fetch_ohlcv_series
    # Create enough data points for initial calculations (e.g., 30 days for 14-period ADX)
    # Need at least 2*14 + buffer = ~35-40 periods for stable calculation
    num_periods = 40
    dates = pd.to_datetime([datetime.date(2025, 4, 30) - datetime.timedelta(days=x) for x in range(num_periods-1, -1, -1)])
    data_df = pd.DataFrame({
        'high': np.linspace(100, 115, num_periods),
        'low': np.linspace(98, 113, num_periods),
        'close': np.linspace(99, 114, num_periods),
        'open': np.linspace(99, 114, num_periods),
        'volume': [1000] * num_periods
    }, index=dates)
    mock_fetch.return_value = data_df

    # 2. Mock Redis
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get.return_value = None # Cache miss
    mock_redis_instance.set = AsyncMock()
    mock_get_redis.return_value = mock_redis_instance

    # 3. Mock the final pandas rolling mean calculation for ADX
    # The agent calculates ATR mean, +DI mean, -DI mean, then ADX mean.
    # We only want to mock the *last* call (the 4th one).
    mock_adx_value = 30.0
    mock_adx_series = MagicMock(spec=pd.Series)
    mock_adx_series.iloc.__getitem__.return_value = mock_adx_value

    # Use side_effect to pass through initial calls and mock the last one
    original_mean = pd.core.window.rolling.Rolling.mean # Store original method
    call_count = 0
    def mean_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 4: # Mock the 4th call (ADX)
            return mock_adx_series
        else: # Pass through other calls to the original method
            # Need to bind the original method to the instance (`args[0]` is `self`)
            return original_mean(args[0], **kwargs)

    mock_pd_mean.side_effect = mean_side_effect

    # 4. Mock Tracker (already patched)
    mock_tracker_update.return_value = None # Simple mock

    # --- Run Agent ---
    res = await adx_run(symbol)

    # --- Assertions ---
    assert res['symbol'] == symbol
    assert res['agent_name'] == agent_name # Use imported name
    assert res['value'] == mock_adx_value # Check the mocked ADX value
    assert res['verdict'] == 'STRONG_TREND' # Based on ADX > 25
    assert res['confidence'] == 1.0 # Based on ADX > 25
    assert res.get('error') is None
    assert 'details' in res
    assert res['details']['adx'] == mock_adx_value

    # --- Verify Mocks ---
    mock_fetch.assert_awaited_once()
    # Check fetch call args
    call_args, call_kwargs = mock_fetch.call_args
    assert call_kwargs.get('symbol') == symbol
    assert isinstance(call_kwargs.get('start_date'), datetime.date)
    assert isinstance(call_kwargs.get('end_date'), datetime.date)
    assert call_kwargs.get('interval') == '1d'

    mock_get_redis.assert_awaited_once()
    mock_redis_instance.get.assert_awaited_once()
    mock_redis_instance.set.assert_awaited_once() # Should cache on success
    mock_tracker_update.assert_called_once_with("technical", agent_name, "implemented")
    # Verify the mocked pandas mean was called 4 times
    assert mock_pd_mean.call_count == 4
    # Verify the iloc access on our mock series (called only on the 4th time)
    mock_adx_series.iloc.__getitem__.assert_called_with(-1)