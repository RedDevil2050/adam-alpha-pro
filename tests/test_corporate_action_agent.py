import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch # Import patch
import httpx # Import httpx for the Response object
from backend.agents.event.corporate_actions_agent import run as ca_run, agent_name # Import agent_name

@pytest.mark.asyncio
# Ensure get_redis_client is mocked as AsyncMock as it's an async function
@patch('backend.agents.decorators.get_redis_client', new_callable=AsyncMock)
@patch('httpx.AsyncClient.get', new_callable=AsyncMock)
async def test_corporate_action_agent(mock_httpx_get, mock_get_redis, monkeypatch): # mock_get_redis is now an AsyncMock
    # Set up Redis mock instance and return value correctly
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get = AsyncMock(return_value=None) # Simulate cache miss
    mock_redis_instance.set = AsyncMock()
    mock_get_redis.return_value = mock_redis_instance

    # Configure the httpx mock response
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    # Simulate an empty list of actions
    mock_response.json.return_value = {"actions": []}
    mock_httpx_get.return_value = mock_response

    # Remove the monkeypatch for fetch_corporate_actions as it's not used by the agent directly in this test setup
    # The agent uses httpx.AsyncClient().get(...) which is what we've patched.

    res = await ca_run('ABC')

    # Assertions based on agent logic for empty actions
    assert res['symbol'] == 'ABC'
    assert res['agent_name'] == agent_name # Use imported agent_name
    assert res['verdict'] == 'NO_DATA' # Agent returns NO_DATA when actions list is empty
    assert res['value'] == 0 # Agent returns count (0) as value for NO_DATA
    assert 'details' in res and res['details']['actions'] == [] # Details should contain empty actions list for NO_DATA from this agent
    assert res.get('error') is None

    # Verify mocks
    mock_httpx_get.assert_awaited_once() # Check httpx was called
    mock_redis_instance.get.assert_awaited_once() # Check cache GET was attempted
    # mock_redis_instance.set.assert_awaited_once() # Cache SET is only called if data is found and processed