import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import pytest
from backend.agents.stealth.moneycontrol_agent import run as mc_run

@pytest.mark.asyncio
async def test_moneycontrol_agent(monkeypatch):
    monkeypatch.setattr('backend.utils.data_provider.fetch_price_alpha_vantage', lambda s: 150.0)
    res = await mc_run('ABC', {})
    assert 'price' in res
    assert isinstance(res['price'], float)