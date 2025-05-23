import pytest
import pandas as pd
import numpy as np
import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from backend.agents.technical.stochastic_agent import run as stoch_run 

@pytest.mark.asyncio
# Patch get_redis_client where it's used by the stochastic_agent's run function
@patch('backend.agents.decorators.get_redis_client', new_callable=AsyncMock) # New patch for the decorator's redis client
@patch('backend.agents.technical.stochastic_agent.get_redis_client', new_callable=AsyncMock) # Existing patch for agent's direct call
async def test_stochastic_agent(mock_get_redis_direct_agent, mock_get_redis_decorator, monkeypatch): # Order of mocks matches patches
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

    # Mock for the direct call in stochastic_agent.run()
    # The existing 'mock_redis_instance' is now 'mock_redis_instance_agent'
    mock_redis_instance_agent = AsyncMock()
    # .get() and .set() on this instance are not called by the agent directly,
    # as those lines are commented out in stochastic_agent.py.
    # Mocking them is harmless but not strictly needed for current agent code.
    mock_redis_instance_agent.get = AsyncMock(return_value=None)
    mock_redis_instance_agent.set = AsyncMock()

    async def fake_get_redis_agent(): # was 'fake_get_redis'
        return mock_redis_instance_agent
    mock_get_redis_direct_agent.side_effect = fake_get_redis_agent # Was mock_get_redis_stoch_agent

    # Mock for the get_redis_client call within the standard_agent_execution decorator
    mock_redis_instance_decorator = AsyncMock()
    mock_redis_instance_decorator.get = AsyncMock(return_value=None) # Simulate cache miss
    mock_redis_instance_decorator.set = AsyncMock() # Decorator will attempt to set cache
    mock_get_redis_decorator.return_value = mock_redis_instance_decorator

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

    mock_get_redis_direct_agent.assert_called_once() # Assert direct call in agent
    # Assert calls made by the decorator via its own redis client
    mock_get_redis_decorator.assert_awaited_once()
    mock_redis_instance_decorator.get.assert_awaited_once()
    mock_redis_instance_decorator.set.assert_awaited_once()