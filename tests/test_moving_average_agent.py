import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import pytest
import pandas as pd
from backend.agents.technical.moving_average_agent import run as ma_run

@pytest.mark.asyncio
async def test_moving_average_agent(monkeypatch):
    prices = pd.Series(range(1, 21))
    monkeypatch.setattr('backend.utils.data_provider.fetch_price_series', lambda symbol: prices)
    res = await ma_run('TCS', {})
    assert 'sma' in res and 'ema' in res