import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import pytest
import pandas as pd
from backend.agents.technical.adx_agent import run as adx_run

@pytest.mark.asyncio
async def test_adx_agent(monkeypatch):
    prices = pd.Series([50 + i for i in range(20)])
    monkeypatch.setattr('backend.utils.data_provider.fetch_price_series', lambda symbol: prices)
    res = await adx_run('TCS', {})
    assert 'adx' in res and 0 <= res['adx'] <= 100