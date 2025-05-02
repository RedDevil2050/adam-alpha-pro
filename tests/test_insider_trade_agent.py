import pytest
from unittest.mock import AsyncMock, patch
from backend.agents.event.insider_trade_agent import run as it_run

@pytest.mark.asyncio
@patch('backend.agents.decorators.get_redis_client')  # Corrected patch target
async def test_insider_trade_agent(mock_get_redis, monkeypatch):
    # Set up Redis mock instance and return value correctly
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get = AsyncMock(return_value=None) # Simulate cache miss
    mock_redis_instance.set = AsyncMock()

    # Configure the mock for get_redis_client to return the instance correctly
    async def fake_get_redis():
        return mock_redis_instance
    mock_get_redis.side_effect = fake_get_redis

    # Mock the data provider function used by the agent
    mock_fetch_trades = AsyncMock(return_value=[]) # Example: return empty list
    monkeypatch.setattr('backend.agents.event.insider_trade_agent.fetch_insider_trades', mock_fetch_trades)

    res = await it_run('ABC')

    # Assertions based on agent's expected output structure
    assert res['symbol'] == 'ABC'
    assert 'value' in res # Agent might put summary/count in value
    assert 'details' in res
    assert 'insider_trades' in res['details']
    assert res['details']['insider_trades'] == []
    assert res['verdict'] == 'NEUTRAL' # Example verdict for no trades
    assert res.get('error') is None

    # Verify mocks
    mock_fetch_trades.assert_awaited_once_with('ABC')
    mock_get_redis.assert_awaited_once() # Verify the patch target was called
    mock_redis_instance.get.assert_awaited_once()
    mock_redis_instance.set.assert_awaited_once()