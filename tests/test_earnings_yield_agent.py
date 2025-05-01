import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import pytest
from backend.agents.valuation.earnings_yield_agent import run as ey_run

@pytest.mark.asyncio
async def test_earnings_yield_agent(monkeypatch):
    monkeypatch.setattr('backend.utils.data_provider.fetch_eps_data', lambda s: 5.0)
    monkeypatch.setattr('backend.utils.data_provider.fetch_price_alpha_vantage', lambda s: 100.0)
    res = await ey_run('ABC')
    assert 'earnings_yield' in res
    assert isinstance(res['earnings_yield'], float)