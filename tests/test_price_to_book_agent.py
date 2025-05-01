import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import asyncio
from backend.agents.valuation.price_to_book_agent import run
from backend.utils.data_provider import fetch_alpha_vantage, fetch_iex

@pytest.mark.asyncio
async def test_price_to_book_agent(monkeypatch):
    async def fake_alpha(endpoint, params):
        return {'BookValue': '20'}
    async def fake_iex(symbol):
        return {'latestPrice': 30.0}
    monkeypatch.setattr('backend.utils.data_provider.fetch_alpha_vantage', fake_alpha)
    monkeypatch.setattr('backend.utils.data_provider.fetch_iex', fake_iex)
    result = await run('TEST')
    assert result['symbol'] == 'TEST'
    assert result['price_to_book'] == round(30.0/20, 2)
    assert result['verdict'] in ['BUY','HOLD','SELL']