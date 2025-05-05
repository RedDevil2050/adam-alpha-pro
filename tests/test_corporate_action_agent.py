import pytest
from unittest.mock import AsyncMock, patch, MagicMock # Added MagicMock
from backend.agents.event.corporate_action_agent import run as ca_run
import httpx # Import httpx

@pytest.mark.asyncio
@patch('backend.agents.decorators.get_redis_client')  # Keep this if decorator is used (agent code shows it's not)
@patch('httpx.AsyncClient.get', new_callable=AsyncMock) # Patch httpx client get
async def test_corporate_action_agent(mock_httpx_get, mock_get_redis, monkeypatch): # Add mock_httpx_get
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

    # Remove the monkeypatch for fetch_corporate_actions as it's not used by the agent
    # monkeypatch.setattr('backend.utils.data_provider.fetch_corporate_actions', AsyncMock(return_value=[]))

    res = await ca_run('ABC')

    # Assertions based on agent logic for empty actions
    assert res['symbol'] == 'ABC'
    assert res['agent_name'] == 'corporate_action_agent'
    assert res['verdict'] == 'NO_DATA' # Agent returns NO_DATA when actions list is empty
    assert res['value'] == 0 # Agent returns count (0) as value for NO_DATA
    assert 'details' in res and res['details'] == {} # Details should be empty
    # The original test asserted 'corporate_actions' in res, which is incorrect for NO_DATA/ERROR
    # assert 'corporate_actions' in res
    # assert res['corporate_actions'] == []
    assert res.get('error') is None

    # Verify mocks
    mock_httpx_get.assert_awaited_once() # Check httpx was called
    mock_redis_instance.get.assert_awaited_once()
    mock_redis_instance.set.assert_awaited_once() # Cache set should be called even for NO_DATA