import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import pandas as pd
from unittest.mock import AsyncMock, patch
from backend.agents.technical.trend_strength_agent import run
import datetime

@pytest.mark.asyncio
@patch('backend.agents.decorators.get_redis_client')  # Updated patch target
async def test_trend_strength_agent(mock_get_redis, monkeypatch):
    # Create realistic OHLCV data with uptrend
    dates = pd.to_datetime([datetime.date(2025, 4, 30) - datetime.timedelta(days=x) for x in range(60, -1, -1)])
    data_df = pd.DataFrame({
        'high': [100 + i * 0.2 for i in range(61)],
        'low': [98 + i * 0.2 for i in range(61)],
        'close': [99 + i * 0.2 for i in range(61)],  # Steady uptrend
        'open': [99 + i * 0.2 for i in range(61)],
        'volume': [1000 + i * 10 for i in range(61)]
    }, index=dates)

    # Mock fetch_ohlcv_series
    mock_fetch = AsyncMock(return_value=data_df)
    monkeypatch.setattr('backend.utils.data_provider.fetch_ohlcv_series', mock_fetch)

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
    assert result['verdict'] in ['STRONG_UPTREND', 'WEAK_UPTREND']  # Expecting uptrend based on data
    assert 'confidence' in result
    assert isinstance(result['confidence'], float)
    assert 'value' in result  # Trend strength score * direction
    assert result['value'] > 0  # Expecting positive score for uptrend
    assert 'details' in result
    assert 'strength_score' in result['details']
    assert 'direction' in result['details']
    assert result['details']['direction'] == 1  # Expecting uptrend direction