import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import pytest
from backend.agents.valuation.pfcf_ratio_agent import run as prun

@pytest.mark.asyncio
async def test_pfcf_ratio_agent(monkeypatch):
    monkeypatch.setattr('backend.utils.data_provider.fetch_price_alpha_vantage', lambda s: 100.0)
    monkeypatch.setattr('backend.utils.data_provider.fetch_cash_flow', lambda s: 10.0)
    res = await prun('ABC', {})
    assert 'pfcf_ratio' in res
    assert isinstance(res['pfcf_ratio'], float)