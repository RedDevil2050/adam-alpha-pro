import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import pytest
from backend.agents.stealth.tickertape_agent import run as tt_run

@pytest.mark.asyncio
async def test_tickertape_agent(monkeypatch):
    monkeypatch.setattr('backend.utils.data_provider.fetch_price_alpha_vantage', lambda s: 200.0)
    res = await tt_run('ABC', {})
    assert 'price' in res
    assert isinstance(res['price'], float)