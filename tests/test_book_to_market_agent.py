import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import pytest
from backend.agents.valuation.book_to_market_agent import run as bm_run

@pytest.mark.asyncio
async def test_book_to_market_agent(monkeypatch):
    monkeypatch.setattr('backend.utils.data_provider.fetch_book_value', lambda s: 50.0)
    monkeypatch.setattr('backend.utils.data_provider.fetch_market_cap', lambda s: 100.0)
    res = await bm_run('ABC', {})
    assert 'book_to_market' in res
    assert isinstance(res['book_to_market'], float)