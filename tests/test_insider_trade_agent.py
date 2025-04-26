import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import pytest
from backend.agents.event.insider_trade_agent import run as it_run

@pytest.mark.asyncio
async def test_insider_trade_agent(monkeypatch):
    monkeypatch.setattr('backend.utils.data_provider.fetch_insider_trades', lambda symbol: [])
    res = await it_run('ABC', {})
    assert 'insider_trades' in res
    assert isinstance(res['insider_trades'], list)