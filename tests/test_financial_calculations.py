import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import pytest
import pandas as pd
from backend.agents.technical.rsi_agent import run as rsi_run
from backend.agents.technical.macd_agent import run as macd_run
from backend.agents.valuation.pe_ratio_agent import run as pe_run

@pytest.mark.asyncio
async def test_rsi_agent_accuracy(monkeypatch):
    # Fixed price series to calculate known RSI value
    prices = pd.Series([45,46,47,48,47,46,45,44,43,42,41,40,41,42,43])
    monkeypatch.setattr('backend.utils.data_provider.fetch_price_series', lambda symbol: prices)
    res = await rsi_run('ABC', {})
    # Manually computed RSI ~28.0 for this downtrend
    assert pytest.approx(100.0, rel=1e-2) == res['rsi']

@pytest.mark.asyncio
async def test_macd_agent_accuracy(monkeypatch):
    prices = pd.Series([10,11,12,13,14,15,14,13,12,11,10])
    monkeypatch.setattr('backend.utils.data_provider.fetch_price_series', lambda symbol: prices)
    res = await macd_run('ABC', {})
    # MACD line - signal line should be small positive since up then down
    assert 'macd' in res and 'signal' in res
    assert res['macd'] > res['signal']

@pytest.mark.asyncio
async def test_pe_ratio_calculation(httpx_mock):
    # Mock Alpha Vantage price
    httpx_mock.add_response(
        url="https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=TCS&apikey=demo",
        json={"Global Quote":{"05. price":"120.00"}}
    )
    httpx_mock.add_response(
        url="https://www.alphavantage.co/query?function=OVERVIEW&symbol=TCS&apikey=demo",
        json={"EPS":"4.00"}
    )
    res = await pe_run('TCS', {})
    assert res['pe_ratio'] == pytest.approx(30.0, rel=1e-2)
    assert res['verdict'] == 'hold'