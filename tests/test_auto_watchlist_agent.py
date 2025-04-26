import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import pytest
from backend.agents.automation.auto_watchlist_agent import run as aw_run

@pytest.mark.asyncio
async def test_auto_watchlist_agent(monkeypatch):
    monkeypatch.setattr('backend.utils.data_provider.fetch_watchlist', lambda: [])
    res = await aw_run('ABC', {})
    assert isinstance(res, dict)