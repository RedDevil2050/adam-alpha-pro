import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import pytest
from backend.agents.automation.ask_alpha_agent import run as ask_run

@pytest.mark.asyncio
async def test_ask_alpha_agent(monkeypatch):
    monkeypatch.setattr('backend.utils.data_provider.fetch_alpha_response', lambda s,q: "response")
    res = await ask_run('ABC', {})
    assert 'response' in res