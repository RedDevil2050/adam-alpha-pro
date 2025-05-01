import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import pandas as pd
import numpy as np
from unittest.mock import AsyncMock, patch
from backend.agents.technical.adx_agent import run as adx_run
import datetime

@pytest.mark.asyncio
@patch('backend.agents.decorators.get_redis_client')  # Updated patch target
async def test_adx_agent(mock_get_redis, monkeypatch):
    # Create realistic OHLCV data (need at least 28 periods for ADX calculation)
    dates = pd.to_datetime([datetime.date(2025, 4, 30) - datetime.timedelta(days=x) for x in range(30, -1, -1)])
    data_df = pd.DataFrame({
        'high': [100 + i * 0.5 + np.random.rand() * 2 for i in range(31)],
        'low': [98 + i * 0.5 - np.random.rand() * 2 for i in range(31)],
        'close': [99 + i * 0.5 for i in range(31)],  # Steady uptrend
        'open': [99 + i * 0.5 - np.random.rand() for i in range(31)],
        'volume': [1000 + i * 10 for i in range(31)]
    }, index=dates)

    # Mock fetch_ohlcv_series correctly
    mock_fetch = AsyncMock(return_value=data_df)
    monkeypatch.setattr('backend.utils.data_provider.fetch_ohlcv_series', mock_fetch)

    # Set up Redis mock instance and return value correctly
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get = AsyncMock(return_value=None)  # Simulate cache miss
    mock_redis_instance.set = AsyncMock()
    mock_get_redis.return_value = mock_redis_instance

    # Mock tracker (optional)
    mock_tracker_update = AsyncMock()
    monkeypatch.setattr('backend.agents.technical.utils.tracker.update', mock_tracker_update)

    # Run the agent
    res = await adx_run('TCS')

    # Verify mocks were called correctly
    mock_fetch.assert_called_once()
    symbol_arg, start_date_arg, end_date_arg, interval_arg = mock_fetch.call_args[0]
    assert symbol_arg == 'TCS'
    assert isinstance(start_date_arg, datetime.date)
    assert isinstance(end_date_arg, datetime.date)
    assert interval_arg == '1d'  # Check default interval

    # Verify Redis operations were called
    mock_redis_instance.get.assert_awaited_once()
    mock_redis_instance.set.assert_awaited_once()

    # Verify results structure and values
    assert 'verdict' in res
    assert 'confidence' in res
    assert 'value' in res  # This is the ADX value
    assert isinstance(res['value'], float)
    assert 0 <= res['value'] <= 100
    assert 'details' in res
    assert 'adx' in res['details']