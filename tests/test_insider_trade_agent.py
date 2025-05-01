import pytest
from unittest.mock import AsyncMock, patch
from backend.agents.event.insider_trade_agent import run as it_run

@pytest.mark.asyncio
@patch('backend.utils.cache_utils.get_redis_client')  # Corrected patch target
async def test_insider_trade_agent(mock_get_redis, monkeypatch):
    # Set up Redis mock instance and return value correctly
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get = AsyncMock(return_value=None) # Simulate cache miss
    mock_redis_instance.set = AsyncMock()
    mock_get_redis.return_value = mock_redis_instance

    monkeypatch.setattr('backend.utils.data_provider.fetch_insider_trades', AsyncMock(return_value=[]))
    res = await it_run('ABC')
    assert 'insider_trades' in res
    assert res['insider_trades'] == []
    
    # Verify cache operations were called correctly
    mock_redis_instance.get.assert_awaited_once()
    mock_redis_instance.set.assert_awaited_once()