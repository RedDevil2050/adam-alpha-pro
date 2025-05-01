import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import pandas as pd
from unittest.mock import AsyncMock, patch
from backend.agents.technical.volume_spike_agent import run
import datetime

@pytest.mark.asyncio
@patch('backend.agents.decorators.get_redis_client')  # Add Redis mock
async def test_volume_spike_agent(mock_get_redis, monkeypatch):
    # Create realistic OHLCV data with a volume spike at the end
    today = datetime.date(2025, 4, 30)
    dates = pd.to_datetime([today - datetime.timedelta(days=x) for x in range(25, -1, -1)])
    volumes = [1000] * 25 + [3000]  # Normal volume, then a spike
    data_df = pd.DataFrame({
        'high': [100 + i * 0.1 for i in range(26)],
        'low': [98 + i * 0.1 for i in range(26)],
        'close': [99 + i * 0.1 for i in range(26)],  # Slight uptrend
        'open': [99 + i * 0.1 for i in range(26)],
        'volume': volumes
    }, index=dates)

    # Mock fetch_ohlcv_series within the agent's module
    mock_fetch = AsyncMock(return_value=data_df)
    monkeypatch.setattr('backend.agents.technical.volume_spike_agent.fetch_ohlcv_series', mock_fetch)

    # Mock get_market_context
    mock_market_context = AsyncMock(return_value={'regime': 'NEUTRAL'})
    monkeypatch.setattr('backend.agents.technical.base.TechnicalAgent.get_market_context', mock_market_context)

    # Set up Redis mock instance and return value correctly
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get = AsyncMock(return_value=None)  # Simulate cache miss
    mock_redis_instance.set = AsyncMock()
    mock_get_redis.return_value = mock_redis_instance

    # Run the agent - pass agent_outputs
    result = await run('TEST', agent_outputs={}) # Pass agent_outputs

    # Verify mocks were called correctly
    mock_fetch.assert_called_once()
    mock_market_context.assert_called_once()
    mock_redis_instance.get.assert_awaited_once()
    mock_redis_instance.set.assert_awaited_once()

    # Verify results
    assert 'verdict' in result
    # Expecting bullish volume due to spike + positive price change
    assert result['verdict'] == 'BULLISH_VOLUME'
    assert 'confidence' in result
    assert isinstance(result['confidence'], float)
    assert 'value' in result  # Volume ratio
    assert result['value'] > 2  # Expecting ratio > 2 due to spike
    assert 'details' in result
    assert 'volume_ratio' in result['details']
    assert 'price_change' in result['details']