import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import asyncio
from backend.agents.valuation.dividend_yield_agent import run
from backend.utils.data_provider import fetch_iex

@pytest.mark.asyncio
async def test_dividend_yield_agent(monkeypatch):
    async def fake_iex(symbol):
        return {'dividendYield': 0.04}
    monkeypatch.setattr('backend.utils.data_provider.fetch_iex', fake_iex)
    result = await run('TEST', {})
    assert result['symbol'] == 'TEST'
    assert result['dividend_yield_pct'] == round(0.04*100, 2)