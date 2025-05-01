import pytest
from unittest.mock import AsyncMock
# Import the agent module itself to patch within it
import backend.agents.forecast.price_forecast_agent as pf_agent

# Mock data for fetch_price_series (should return a list or Series of prices)
MOCK_PRICES = [100.0, 101.0, 102.0, 101.5, 103.0] # Example price series

# Mock the fetch_price_series function
async def fake_fetch_prices(symbol, source_preference=None):
    return MOCK_PRICES

@pytest.mark.asyncio
async def test_price_forecast_agent(monkeypatch):
    # Mock redis client get/set methods
    mock_redis_get = AsyncMock(return_value=None) # Simulate cache miss
    mock_redis_set = AsyncMock()
    mock_redis_client = AsyncMock()
    mock_redis_client.get = mock_redis_get
    mock_redis_client.set = mock_redis_set
    # Need to mock the awaitable get_redis_client used within the agent
    async def mock_get_redis():
        return mock_redis_client
    # Patch get_redis_client where it's imported in the agent module
    monkeypatch.setattr(pf_agent, 'get_redis_client', mock_get_redis)

    # Patch fetch_price_series where it's imported in the agent module
    monkeypatch.setattr(pf_agent, 'fetch_price_series', fake_fetch_prices)

    # Call run with only the symbol argument
    result = await pf_agent.run('TEST')

    assert result['symbol'] == 'TEST'
    # Check for keys based on the agent's actual return structure
    assert result['agent_name'] == pf_agent.agent_name
    assert 'verdict' in result # e.g., UPTREND, DOWNTREND
    assert 'confidence' in result
    assert 'value' in result # Slope value
    assert 'details' in result and 'slope' in result['details']
    assert 'score' in result

    # Verify cache get was called
    mock_redis_get.assert_awaited_once_with(f"{pf_agent.agent_name}:TEST")
    # Verify cache set was called
    mock_redis_set.assert_awaited_once()

@pytest.mark.asyncio
async def test_price_forecast_agent_cache_hit(monkeypatch):
    # Mock redis client get/set methods for cache hit
    cached_data = {"symbol": "TEST", "verdict": "CACHED_TREND", "confidence": 0.99}
    mock_redis_get = AsyncMock(return_value=cached_data) # Simulate cache hit
    mock_redis_set = AsyncMock()
    mock_redis_client = AsyncMock()
    mock_redis_client.get = mock_redis_get
    mock_redis_client.set = mock_redis_set
    async def mock_get_redis():
        return mock_redis_client
    monkeypatch.setattr(pf_agent, 'get_redis_client', mock_get_redis)

    # Patch fetch_price_series - it shouldn't be called on cache hit
    mock_fetch_prices = AsyncMock()
    monkeypatch.setattr(pf_agent, 'fetch_price_series', mock_fetch_prices)

    # Call run
    result = await pf_agent.run('TEST')

    # Assertions for cache hit
    assert result == cached_data # Should return the cached data
    mock_redis_get.assert_awaited_once_with(f"{pf_agent.agent_name}:TEST")
    mock_fetch_prices.assert_not_awaited() # Fetch should not be called
    mock_redis_set.assert_not_awaited() # Set should not be called