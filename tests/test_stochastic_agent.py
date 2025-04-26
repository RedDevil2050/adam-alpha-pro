import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import pytest
import pandas as pd
from backend.agents.technical.stochastic_agent import run as stoch_run

@pytest.mark.asyncio
async def test_stochastic_agent(monkeypatch):
    prices = pd.Series([10,12,11,13,12,14,13,15,14,16,15,17,16,18,17])
    monkeypatch.setattr('backend.utils.data_provider.fetch_price_series', lambda symbol: prices)
    res = await stoch_run('TCS', {})
    assert 'percent_k' in res and 'percent_d' in res
    assert 0 <= res['percent_k'] <= 100
    assert 0 <= res['percent_d'] <= 100