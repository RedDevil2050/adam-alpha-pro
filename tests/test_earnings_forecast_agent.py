import pytest
from unittest.mock import AsyncMock
import backend.agents.forecast.earnings_forecast_agent as ef_agent

# Mock data for fetch_iex_earnings
async def fake_earnings(symbol):
    return {'earnings': [{'actualEPS': 1.5, 'consensusEPS': 1.4, 'fiscalPeriod': 'Q1 2023'}]}

@pytest.mark.asyncio
async def test_earnings_forecast_agent(monkeypatch):
    # Mock redis client get/set methods
    mock_redis_get = AsyncMock(return_value=None) # Simulate cache miss
    mock_redis_set = AsyncMock()
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get = mock_redis_get
    mock_redis_instance.set = mock_redis_set
    # Need to mock the awaitable get_redis_client
    async def mock_get_redis():
        return mock_redis_instance
    # Patch where get_redis_client is USED (decorators module)
    monkeypatch.setattr('backend.agents.decorators.get_redis_client', mock_get_redis)

    # Patch the fetch_iex_earnings used within the module
    monkeypatch.setattr(ef_agent, 'fetch_iex_earnings', fake_earnings)

    # Call run with only the symbol argument
    result = await ef_agent.run('TEST')

    assert result['symbol'] == 'TEST'
    assert 'forecast' in result
    assert len(result['forecast']) > 0
    assert result['forecast'][0]['actualEPS'] == 1.5
    # Verify cache set was called
    mock_redis_set.assert_awaited_once()
    # Verify cache get was called
    mock_redis_get.assert_awaited_once()