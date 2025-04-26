import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import asyncio
from backend.agents.valuation.eps_agent import run
from backend.utils.data_provider import fetch_alpha_vantage

@pytest.mark.asyncio
async def test_eps_agent(monkeypatch):
    async def fake_alpha(endpoint, params):
        return {'EPS': '10.5'}
    monkeypatch.setattr('backend.utils.data_provider.fetch_alpha_vantage', fake_alpha)
    result = await run('TEST', {})
    assert result['symbol'] == 'TEST'
    assert result['eps'] == 10.5
    assert result['verdict'] in ['BUY', 'HOLD']
    assert 'confidence' in result