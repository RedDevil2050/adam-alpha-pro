import pytest
from unittest.mock import AsyncMock, patch
from backend.agents.event.earnings_calendar_agent import run as ec_run

@pytest.mark.asyncio
@patch('backend.agents.decorators.get_redis_client')  # Updated patch target
async def test_earnings_calendar_agent(mock_get_redis, monkeypatch):
    # Set up Redis mock instance and return value correctly
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get = AsyncMock(return_value=None) # Simulate cache miss
    mock_redis_instance.set = AsyncMock()
    mock_get_redis.return_value = mock_redis_instance

    monkeypatch.setattr('backend.utils.data_provider.fetch_earnings_calendar', AsyncMock(return_value=[]))
    res = await ec_run('ABC')
    assert 'earnings_calendar' in res
    assert res['earnings_calendar'] == []
    
    # Verify cache operations were called correctly
    mock_redis_instance.get.assert_awaited_once()
    mock_redis_instance.set.assert_awaited_once()