import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import pytest
from backend.agents.automation.bulk_portfolio_agent import run as bp_run

@pytest.mark.asyncio
async def test_bulk_portfolio_agent(monkeypatch):
    monkeypatch.setattr('backend.utils.data_provider.fetch_portfolio', lambda: [])
    res = await bp_run('ABC', {})
    assert isinstance(res, dict)