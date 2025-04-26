import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import pytest
from backend.agents.event.corporate_action_agent import run as ca_run

@pytest.mark.asyncio
async def test_corporate_action_agent(monkeypatch):
    monkeypatch.setattr('backend.utils.data_provider.fetch_corporate_actions', lambda symbol: [])
    res = await ca_run('ABC', {})
    assert 'corporate_actions' in res
    assert isinstance(res['corporate_actions'], list)