import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from backend.agents.valuation.reverse_dcf_agent import run as rdcf_run

@pytest.mark.asyncio
async def test_reverse_dcf_agent(monkeypatch):
    # Stub price, cash flows, and discount rate
    monkeypatch.setattr('backend.utils.data_provider.fetch_price_alpha_vantage', lambda symbol: 100.0)
    monkeypatch.setattr('backend.utils.data_provider.fetch_cash_flows', lambda symbol: [10, 10, 10])
    monkeypatch.setattr('backend.utils.data_provider.fetch_discount_rate', lambda symbol: 0.1)
    res = await rdcf_run('ABC', {})
    assert 'reverse_dcf' in res
    assert isinstance(res['reverse_dcf'], float)