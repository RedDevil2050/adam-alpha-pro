import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from backend.agents.automation.ask_alpha_agent import run as ask_run, agent_name # Import agent_name

@pytest.mark.asyncio
async def test_ask_alpha_agent_default_question(monkeypatch): # Renamed and updated test
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