import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import pandas as pd
import numpy as np
from unittest.mock import AsyncMock, patch, MagicMock
from backend.agents.technical.adx_agent import run as adx_run
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
    # 1. Mock fetch_ohlcv_series
    # Create enough data points for initial calculations (e.g., 30 days)
    dates = pd.to_datetime([datetime.date(2025, 4, 30) - datetime.timedelta(days=x) for x in range(30, -1, -1)])
    data_df = pd.DataFrame({
        'high': np.linspace(100, 115, 31),
        'low': np.linspace(98, 113, 31),
        'close': np.linspace(99, 114, 31),
        'open': np.linspace(99, 114, 31),
        'volume': [1000] * 31
    }, index=dates)
    mock_fetch.return_value = data_df

    # 2. Mock Redis
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get.return_value = None # Cache miss
    mock_redis_instance.set = AsyncMock()
    mock_get_redis.return_value = mock_redis_instance

    # 3. Mock the final pandas rolling mean calculation for ADX
    # Create a mock Series-like object with an iloc attribute
    mock_adx_series = MagicMock()
    mock_adx_series.iloc.__getitem__.return_value = 30.0 # Mock ADX value > 25
    # Make the mock_pd_mean return our mock series when called the last time (for ADX)
    # This is a simplification; real usage might require more specific side_effect logic
    # Assuming the last .mean() call is the one for ADX
    mock_pd_mean.return_value = mock_adx_series 

    # 4. Mock Tracker (already patched)
    mock_tracker_update.return_value = None # Simple mock

    # --- Run Agent ---
    res = await adx_run('TEST_SYMBOL')

    # --- Assertions ---
    assert res['symbol'] == 'TEST_SYMBOL'
    assert res['agent_name'] == 'adx_agent'
    assert res['value'] == 30.0 # Check the mocked ADX value
    assert res['verdict'] == 'STRONG_TREND' # Based on ADX > 25
    assert res['confidence'] == 1.0 # Based on ADX > 25
    assert res.get('error') is None
    assert 'details' in res
    assert res['details']['adx'] == 30.0

    # --- Verify Mocks ---
    mock_fetch.assert_awaited_once()
    # Check fetch call args
    call_args, call_kwargs = mock_fetch.call_args
    assert call_kwargs.get('symbol') == 'TEST_SYMBOL'
    assert isinstance(call_kwargs.get('start_date'), datetime.date)
    assert isinstance(call_kwargs.get('end_date'), datetime.date)
    assert call_kwargs.get('interval') == '1d'

    mock_get_redis.assert_awaited_once()
    mock_redis_instance.get.assert_awaited_once()
    mock_redis_instance.set.assert_awaited_once() # Should cache on success
    mock_tracker_update.assert_called_once_with("technical", "adx_agent", "implemented")
    # Verify the mocked pandas mean was called (likely multiple times)
    assert mock_pd_mean.called
    # Verify the iloc access on our mock series
    mock_adx_series.iloc.__getitem__.assert_called_with(-1)