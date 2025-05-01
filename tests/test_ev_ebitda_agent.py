import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import asyncio
from backend.agents.valuation.ev_ebitda_agent import run
from backend.utils.data_provider import fetch_alpha_vantage, fetch_iex

@pytest.mark.asyncio
async def test_ev_ebitda_agent(monkeypatch):
    async def fake_alpha(endpoint, params):
        return {'EnterpriseValue': '2000', 'EBITDA': '100'}
    async def fake_iex(symbol):
        return {}
    monkeypatch.setattr('backend.utils.data_provider.fetch_alpha_vantage', fake_alpha)
    monkeypatch.setattr('backend.utils.data_provider.fetch_iex', fake_iex)
    result = await run('TEST')
    assert result['symbol'] == 'TEST'
    assert result['ev_ebitda'] == round(2000/100, 2)
    assert result['verdict'] in ['BUY','HOLD','SELL']