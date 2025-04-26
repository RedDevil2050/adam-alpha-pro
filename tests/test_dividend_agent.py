import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from backend.agents.valuation.dividend_agent import run as div_run

@pytest.mark.asyncio
async def test_dividend_agent(monkeypatch):
    # Stub dividend yield to 5%
    monkeypatch.setattr('backend.utils.data_provider.fetch_dividend_yield', lambda symbol: 0.05)
    res = await div_run('ABC', {})
    assert 'dividend_yield' in res
    assert isinstance(res['dividend_yield'], float)
    assert pytest.approx(0.05, rel=1e-2) == res['dividend_yield']