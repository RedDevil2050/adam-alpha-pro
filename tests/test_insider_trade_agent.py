import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from backend.agents.event.insider_trade_agent import run as it_run

@pytest.mark.asyncio
# Correct patch target: where get_redis_client is IMPORTED/USED in the agent module
@patch('backend.agents.event.insider_trade_agent.get_redis_client')
async def test_insider_trade_agent(mock_get_redis, monkeypatch):
    # Set up Redis mock instance and return value correctly
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get = AsyncMock(return_value=None) # Simulate cache miss
    mock_redis_instance.set = AsyncMock()
    async def fake_get_redis():
        return mock_redis_instance
    mock_get_redis.return_value = mock_redis_instance # Directly set return_value

    # Mock the data provider function used by the agent
    mock_fetch_trades = AsyncMock(return_value=[]) # Example: return empty list
    monkeypatch.setattr('backend.agents.event.insider_trade_agent.fetch_insider_trades', mock_fetch_trades)

    # Mock the tracker update to prevent errors if tracker isn't fully set up in test env
    monkeypatch.setattr('backend.agents.event.insider_trade_agent.tracker.update', MagicMock())

    res = await it_run('ABC')

    # Assertions based on agent's expected output structure
    assert res['symbol'] == 'ABC'
    assert 'value' in res # Agent might put summary/count in value
    assert 'details' in res
    # Assert 'insider_trades' is directly in the result, not nested
    assert 'insider_trades' in res
    assert res['insider_trades'] == []
    # Updated expected verdict for empty trades list
    assert res['verdict'] == 'NEUTRAL'
    assert res.get('error') is None

    # Verify mocks
    mock_fetch_trades.assert_awaited_once_with('ABC')
    mock_get_redis.assert_awaited_once() # Verify the patch target was called
    mock_redis_instance.get.assert_awaited_once()
    mock_redis_instance.set.assert_awaited_once() # Set should be called even for NEUTRAL