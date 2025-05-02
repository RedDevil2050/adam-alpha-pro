import pytest
import pandas as pd
import numpy as np
import datetime
from unittest.mock import AsyncMock, MagicMock, patch # Add patch to imports
from backend.agents.technical.stochastic_agent import run as stoch_run

@pytest.mark.asyncio
@patch('backend.agents.decorators.get_redis_client') # Correct patch target
async def test_stochastic_agent(mock_get_redis, monkeypatch):
    # Create realistic OHLCV data (need enough for window, default K=14, D=3)
    dates = pd.to_datetime([datetime.date(2025, 4, 30) - datetime.timedelta(days=x)
                            for x in range(20, -1, -1)])
    # Create data that should result in oversold condition (low close relative to high/low range)
    lows = [90 - i * 0.1 for i in range(21)]
    highs = [110 + i * 0.1 for i in range(21)]
    closes = [92 - i * 0.05 for i in range(21)] # Close near the low
    data_df = pd.DataFrame({
        'high': highs,
        'low': lows,
        'close': closes,
        'open': [c + np.random.rand() for c in closes],
        'volume': [1000 + i * 10 for i in range(21)]
    }, index=dates)

    # Mock fetch_ohlcv_series correctly within the agent's module
    mock_fetch = AsyncMock(return_value=data_df)
    monkeypatch.setattr('backend.agents.technical.stochastic_agent.fetch_ohlcv_series', mock_fetch)

    # Set up Redis mock instance and return value correctly
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get = AsyncMock(return_value=None) # Simulate cache miss
    mock_redis_instance.set = AsyncMock()

    # Configure the mock for get_redis_client to return the instance correctly
    async def fake_get_redis():
        return mock_redis_instance
    mock_get_redis.side_effect = fake_get_redis

    # Mock tracker (optional)
    mock_tracker_update = AsyncMock()
    # Try both possible tracker import paths
    for tracker_path in [
        'backend.agents.technical.stochastic_agent.tracker.update',
        'backend.agents.technical.utils.tracker.update',
        'backend.monitor.tracker.get_tracker' # Add path to get_tracker used by decorator
    ]:
        try:
            # If patching get_tracker, make it return a mock tracker instance
            if tracker_path.endswith('get_tracker'):
                mock_tracker_instance = MagicMock()
                mock_tracker_instance.update_agent_status = AsyncMock()
                monkeypatch.setattr(tracker_path, MagicMock(return_value=mock_tracker_instance))
            else:
                monkeypatch.setattr(tracker_path, mock_tracker_update)
            # Don't break, try patching all known paths where tracker might be used
        except AttributeError:
            continue

    # Call the agent run function - pass agent_outputs
    res = await stoch_run('TCS', agent_outputs={}) # Pass agent_outputs

    # Assertions
    assert 'details' in res
    assert 'k' in res['details']
    assert 'd' in res['details']
    assert 'value' in res # 'value' holds the latest K
    # Recalculate expected K based on data to be more precise
    # K = 100 * (Close - Low_14) / (High_14 - Low_14)
    low_14 = data_df['low'].rolling(14).min()
    high_14 = data_df['high'].rolling(14).max()
    k_series = 100 * (data_df['close'] - low_14) / (high_14 - low_14)
    d_series = k_series.rolling(3).mean()
    expected_k = k_series.iloc[-1]
    expected_d = d_series.iloc[-1]

    assert res['value'] == pytest.approx(expected_k) # Expecting oversold based on data (K < 20 default)
    assert res['details']['k'] == pytest.approx(expected_k)
    assert res['details']['d'] == pytest.approx(expected_d)
    # Assert the verdict based on agent logic (K < 20 -> BUY)
    assert res['verdict'] == 'BUY'
    assert 'confidence' in res
    assert res.get('error') is None

    # Verify mocks were called
    mock_fetch.assert_called_once()
    mock_get_redis.assert_awaited_once() # Verify the patch target was called
    # Assert on the instance's methods directly
    mock_redis_instance.get.assert_awaited_once()
    mock_redis_instance.set.assert_awaited_once()