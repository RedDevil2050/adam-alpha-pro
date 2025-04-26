import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import asyncio
from backend.agents.valuation.price_target_agent import run
from backend.utils.data_provider import fetch_iex

@pytest.mark.asyncio
async def test_price_target_agent(monkeypatch):
    async def fake_iex(symbol):
        return {'week52Low': 80.0, 'week52High': 120.0, 'latestPrice': 100.0}
    monkeypatch.setattr('backend.utils.data_provider.fetch_iex', fake_iex)
    result = await run('TEST', {})
    assert result['symbol'] == 'TEST'
    assert result['price_target'] == round((80+120)/2, 2)