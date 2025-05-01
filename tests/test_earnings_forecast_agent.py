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

    # Patch the fetch_eps_data used within the module
    monkeypatch.setattr(ef_agent, 'fetch_eps_data', AsyncMock(return_value={2022: 1.0, 2023: 1.5})) # Mock fetch_eps_data

    # Call run with only the symbol argument
    result = await ef_agent.run('TEST')

    assert result['symbol'] == 'TEST'
    # Assert based on trend calculation
    assert result['verdict'] == 'UPTREND' # Based on 1.0 -> 1.5
    assert result['value'] == pytest.approx(0.5) # Trend = 1.5 - 1.0
    assert 'confidence' in result
    assert result['confidence'] > 0 # Should be positive for uptrend
    assert 'score' in result
    assert result['score'] > 0
    assert 'details' in result
    assert result['details']['eps_trend'] == pytest.approx(0.5)
    # Verify cache set was called
    mock_redis_set.assert_awaited_once()
    # Verify cache get was called
    mock_redis_get.assert_awaited_once()