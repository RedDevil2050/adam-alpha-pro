import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import pytest
from backend.agents.event.earnings_calendar_agent import run as ec_run

@pytest.mark.asyncio
async def test_earnings_calendar_agent(monkeypatch):
    monkeypatch.setattr('backend.utils.data_provider.fetch_earnings_calendar', lambda symbol: [])
    res = await ec_run('ABC', {})
    assert 'earnings_calendar' in res
    assert isinstance(res['earnings_calendar'], list)