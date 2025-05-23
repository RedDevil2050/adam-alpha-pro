import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from backend.agents.event.insider_trade_agent import run as it_run

@pytest.mark.asyncio
# Patch order: innermost decorator corresponds to the first argument after self/cls
@patch('backend.agents.base.get_redis_client', new_callable=AsyncMock)      # For AgentBase.initialize
@patch('backend.agents.event.insider_trade_agent.get_redis_client', new_callable=AsyncMock) # For @cache_agent_result decorator (if used)
async def test_insider_trade_agent(
    mock_decorator_get_redis_client, # Corresponds to event.insider_trade_agent.get_redis_client
    mock_base_get_redis_client,      # Corresponds to base.get_redis_client
    monkeypatch
):
    # Set up Redis mock instance and return value correctly for both mocks
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get = AsyncMock(return_value=None) # Simulate cache miss
    mock_redis_instance.set = AsyncMock()
    
    mock_decorator_get_redis_client.return_value = mock_redis_instance
    mock_base_get_redis_client.return_value = mock_redis_instance

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
    assert res.get('error') is None, f"Agent returned error: {res.get('error')}"

    # Verify mocks
    mock_fetch_trades.assert_awaited_once_with('ABC')
    mock_decorator_get_redis_client.assert_awaited_once() # Verify the patch target was called
    mock_base_get_redis_client.assert_awaited_once()      # Verify the patch target was called
    # Check that get is called at least once (by decorator or base)
    assert mock_redis_instance.get.await_count >= 1
    # Set should be called if no error and verdict is not NO_DATA
    if res.get('verdict') not in ['NO_DATA', 'ERROR', None]:
        assert mock_redis_instance.set.await_count >= 1