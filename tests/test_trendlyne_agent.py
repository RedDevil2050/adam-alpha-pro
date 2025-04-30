import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import pytest
from backend.agents.stealth.trendlyne_agent import run as tr_run

@pytest.fixture(autouse=True)
def mock_fetch_price_alpha_vantage(monkeypatch):
    async def mock_fetch(symbol):
        return {"price": 100.0}
    monkeypatch.setattr('backend.utils.data_provider.fetch_price_alpha_vantage', mock_fetch)

@pytest.mark.asyncio
async def test_trendlyne_agent(monkeypatch):
    res = await tr_run('ABC', {})
    assert 'symbol' in res
    assert 'verdict' in res
    assert 'confidence' in res
    assert isinstance(res['confidence'], float)
    assert res['symbol'] == 'ABC'