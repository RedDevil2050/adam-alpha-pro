import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import pandas as pd
from unittest.mock import AsyncMock, patch
from backend.agents.technical.moving_average_agent import run as ma_run
import datetime

@pytest.mark.asyncio
@patch('backend.agents.decorators.get_redis_client')  # Updated patch target
async def test_moving_average_agent(mock_get_redis, monkeypatch):
    # Create realistic OHLCV data with uptrend
    dates = pd.to_datetime([datetime.date(2025, 4, 30) - datetime.timedelta(days=x) for x in range(25, -1, -1)])
    prices_df = pd.DataFrame({
        'high': range(101, 127),  # Length 26
        'low': range(99, 125),    # Length 26
        'close': range(100, 126),  # Length 26, increasing trend
        'open': range(100, 126),   # Length 26
        'volume': [1000] * 26      # Length 26
    }, index=dates)

    # Mock fetch_ohlcv_series
    mock_fetch = AsyncMock(return_value=prices_df)
    monkeypatch.setattr('backend.utils.data_provider.fetch_ohlcv_series', mock_fetch)

    # Set up Redis mock instance and return value correctly
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get = AsyncMock(return_value=None)  # Simulate cache miss
    mock_redis_instance.set = AsyncMock()
    mock_get_redis.return_value = mock_redis_instance

    # Mock tracker (optional)
    mock_tracker_update = AsyncMock()
    monkeypatch.setattr('backend.agents.technical.utils.tracker.update', mock_tracker_update)

    # Run the agent with a specific window
    window = 20
    res = await ma_run('TCS', window=window)

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

    # Verify results
    assert 'verdict' in res
    assert res['verdict'] == 'BUY'  # Based on increasing price data
    assert 'confidence' in res
    assert res['confidence'] > 0  # Should have positive confidence
    assert 'value' in res  # Slope percentage
    assert res['value'] > 0  # Slope should be positive
    assert 'details' in res
    assert 'ma_last' in res['details']