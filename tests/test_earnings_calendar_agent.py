import pytest
from unittest.mock import AsyncMock, patch
# Import the agent's run function and agent_name
from backend.agents.event.earnings_calendar_agent import run as ec_run, agent_name

@pytest.mark.asyncio
# Correct patch target for redis client used directly by the agent
@patch('backend.agents.event.earnings_calendar_agent.get_redis_client')
async def test_earnings_calendar_agent(mock_get_redis, monkeypatch):
    # Set up Redis mock instance and return value correctly
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get = AsyncMock(return_value=None) # Simulate cache miss
    mock_redis_instance.set = AsyncMock()
    # Configure the mock factory to return the instance when awaited
    mock_get_redis.return_value = mock_redis_instance

    # Mock the data provider to return no data (empty dict or list, depending on provider)
    # Let's assume it returns an empty dict for no data found
    mock_fetch = AsyncMock(return_value={})
    monkeypatch.setattr('backend.agents.event.earnings_calendar_agent.fetch_earnings_calendar', mock_fetch)

    # Mock the tracker update as it might not be fully set up
    monkeypatch.setattr('backend.agents.event.earnings_calendar_agent.tracker.update', AsyncMock()) # Use AsyncMock if tracker.update is async

    # --- Run Agent ---
    res = await ec_run('ABC')

    # --- Assertions for NO_DATA case ---
    assert res['symbol'] == 'ABC'
    assert res['agent_name'] == agent_name
    assert res['verdict'] == 'NO_DATA'
    assert res['value'] is None
    assert res['details'] == {} # Expect empty details for NO_DATA
    assert res.get('error') is None

    # --- Verify Mocks ---
    mock_fetch.assert_awaited_once_with('ABC')
    mock_get_redis.assert_awaited_once() # Verify redis client factory was awaited
    mock_redis_instance.get.assert_awaited_once_with(f"{agent_name}:ABC") # Check cache key
    # Cache set should be called even for NO_DATA if caching is implemented for it
    # Based on agent code, it caches NO_DATA result.
    mock_redis_instance.set.assert_awaited_once()