import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import pytest
import pandas as pd
from backend.agents.technical.supertrend_agent import run as st_run

@pytest.mark.asyncio
async def test_supertrend_agent(monkeypatch):
    prices = pd.DataFrame({'high':[10,12,11,13,12,14,13,15,14,16],
                           'low':[8,9,9,10,10,11,11,12,12,13],
                           'close':[9,11,10,12,11,13,12,14,13,15]})
    monkeypatch.setattr('backend.utils.data_provider.fetch_ohlcv_series', lambda symbol: prices)
    res = await st_run('TCS', {})
    assert 'supertrend' in res
    assert res['supertrend'] in ['buy','sell','hold']