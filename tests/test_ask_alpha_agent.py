import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from backend.agents.automation.ask_alpha_agent import run as ask_run, agent_name # Import agent_name
from unittest.mock import AsyncMock, patch # Import patch

@pytest.mark.asyncio
@patch('backend.agents.automation.ask_alpha_agent.get_redis_client', new_callable=AsyncMock) # Updated patch
async def test_ask_alpha_agent_default_question(mock_get_redis_client, monkeypatch): # Add mock_get_redis_client
    # Simulate the redis client
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get.return_value = None  # Simulate cache miss
    mock_redis_instance.set = AsyncMock()
    mock_get_redis_client.return_value = mock_redis_instance

    # When question is empty, the agent constructs a default response.
    # No external fetch function (like the previously mocked fetch_alpha_response) is called for this path.
    res = await ask_run('ABC', {}) # question defaults to ""
    
    expected_answer = "No specialized answer, try asking about price, EPS, or recommendation."
    
    assert res['symbol'] == 'ABC'
    assert res['agent_name'] == agent_name
    assert res['verdict'] == 'INFO'
    assert res['confidence'] == 1.0
    assert res['value'] == expected_answer
    assert 'details' in res
    assert res['details']['answer'] == expected_answer
    assert res.get('error') is None

    # Verify that cache set was called
    mock_redis_instance.set.assert_awaited_once()