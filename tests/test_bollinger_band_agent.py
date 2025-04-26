import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import pytest
import pandas as pd
from backend.agents.technical.bollinger_band_agent import run as bb_run

@pytest.mark.asyncio
async def test_bollinger_band_agent(monkeypatch):
    prices = pd.Series([i + (i % 2) for i in range(30)])
    monkeypatch.setattr('backend.utils.data_provider.fetch_price_series', lambda symbol: prices)
    res = await bb_run('TCS', {})
    assert 'upper_band' in res and 'lower_band' in res and 'middle_band' in res
    assert res['upper_band'] >= res['lower_band']