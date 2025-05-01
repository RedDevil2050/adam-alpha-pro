import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest.mock import AsyncMock, patch
from backend.agents.valuation.dividend_yield_agent import run

@pytest.mark.asyncio
@patch('backend.agents.decorators.get_redis_client')  # Add Redis mock
async def test_dividend_yield_agent(mock_get_redis, monkeypatch):
    # Mock IEX data with all potentially needed fields
    async def fake_iex(symbol):
        return {
            'dividend_yield_pct': 4.0,  # Match the field name expected by the agent
            'dividendYield': 0.04,      # Include original format too just in case
            'latestPrice': 100.0,       # Include price data
            'peRatio': 15.0,            # Include other fields that might be used
            'sector': 'Technology'
        }
    monkeypatch.setattr('backend.utils.data_provider.fetch_iex', fake_iex)

    # Set up Redis mock instance
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get = AsyncMock(return_value=None)  # Simulate cache miss
    mock_redis_instance.set = AsyncMock()
    mock_get_redis.return_value = mock_redis_instance

    # Run the agent
    result = await run('TEST')

    # Verify Redis operations
    mock_redis_instance.get.assert_awaited_once()
    mock_redis_instance.set.assert_awaited_once()

    # Verify results
    assert result['symbol'] == 'TEST'
    assert result['dividend_yield_pct'] == 4.0  # Should be in percentage form
    assert 'verdict' in result
    assert 'confidence' in result
    assert isinstance(result['confidence'], float)
    assert 0 <= result['confidence'] <= 1.0