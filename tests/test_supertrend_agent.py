import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import pandas as pd
from unittest.mock import AsyncMock, patch
from backend.agents.technical.supertrend_agent import run as st_run
import datetime

@pytest.mark.asyncio
@patch('backend.utils.cache_utils.get_redis_client') # Correct patch target
async def test_supertrend_agent(mock_get_redis, monkeypatch):
    # Mock data matching expected OHLCV structure
    dates = pd.to_datetime([datetime.date.today() - datetime.timedelta(days=x) for x in range(9, -1, -1)])
    prices = pd.DataFrame({
        'high': [10, 12, 11, 13, 12, 14, 13, 15, 14, 16],
        'low': [8, 9, 9, 10, 10, 11, 11, 12, 12, 13],
        'close': [9, 11, 10, 12, 11, 13, 12, 14, 13, 15],
        'open': [8.5, 10.5, 9.5, 11.5, 10.5, 12.5, 11.5, 13.5, 12.5, 14.5],
        'volume': [1000] * 10
    }, index=dates)

    # Mock fetch_ohlcv_series within the agent's module
    mock_fetch = AsyncMock(return_value=prices)
    monkeypatch.setattr('backend.agents.technical.supertrend_agent.fetch_ohlcv_series', mock_fetch)

    # Mock get_market_context 
    mock_market_context = AsyncMock(return_value={'volatility': 0.2, 'regime': 'NEUTRAL'})
    monkeypatch.setattr('backend.agents.technical.base.TechnicalAgent.get_market_context', mock_market_context)

    # Set up Redis mock instance and return value correctly
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get = AsyncMock(return_value=None)  # Simulate cache miss
    mock_redis_instance.set = AsyncMock()
    mock_get_redis.return_value = mock_redis_instance

    # Run the agent - pass agent_outputs explicitly
    res = await st_run('TCS', agent_outputs={}) # Pass agent_outputs

    # Verify mocks were called correctly
    mock_fetch.assert_called_once()
    mock_market_context.assert_called_once()
    mock_redis_instance.get.assert_awaited_once()
    mock_redis_instance.set.assert_awaited_once()

    # Verify results
    assert 'verdict' in res
    assert res['verdict'] in ['BUY', 'SELL', 'HOLD', 'NO_DATA', 'ERROR']  # Allow for different outcomes
    assert 'value' in res  # Supertrend value
    assert 'confidence' in res
    assert isinstance(res['confidence'], float)  # Ensure confidence is a float
    assert 0 <= res['confidence'] <= 1  # Confidence should be between 0 and 1