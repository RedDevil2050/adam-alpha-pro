import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import pytest
import pandas as pd
from backend.agents.technical.rsi_agent import run as rsi_run
from backend.agents.technical.macd_agent import run as macd_run
from backend.agents.risk.beta_agent import run as beta_run
from backend.agents.risk.volatility_level_agent import run as vol_run 
from backend.agents.valuation.dcf_agent import run as dcf_run
from backend.agents.risk.sharpe_agent import run as sharpe_run
from backend.agents.risk.drawdown_agent import run as drawdown_run
from backend.agents.valuation.peg_ratio_agent import run as peg_run
from backend.agents.valuation.ev_ebitda_agent import run as ev_run

@pytest.mark.asyncio
async def test_rsi_agent_precision(monkeypatch):
    # Up/Down series for RSI=100 exactly
    prices = pd.Series(list(range(1, 16)) + list(range(15, 0, -1)))
    monkeypatch.setattr('backend.utils.data_provider.fetch_price_series', lambda symbol: prices)
    res = await rsi_run('TST')
    assert pytest.approx(100.0, rel=1e-2) == res['rsi']

@pytest.mark.asyncio
async def test_macd_agent_precision(monkeypatch):
    prices = pd.Series([i for i in range(1,30)])
    monkeypatch.setattr('backend.utils.data_provider.fetch_price_series', lambda symbol: prices)
    res = await macd_run('TST')
    # Compare to expected using last 3 values (approx)
    assert pytest.approx(res['macd'], rel=0.1) == res['signal'] or res['macd'] > res['signal']

@pytest.mark.asyncio
async def test_beta_and_volatility(monkeypatch):
    prices = pd.Series([1,2,3,4,5,6,7,8,9,10])
    # Beta: perfectly correlated to market
    monkeypatch.setattr('backend.utils.data_provider.fetch_price_series', lambda symbol: prices)
    # For beta, also stub fetch_market_series if required
    # The mock below overwrites the previous one, ensure it's intended or use different mocks if needed
    monkeypatch.setattr('backend.utils.data_provider.fetch_price_series', lambda symbol: prices)
    res_beta = await beta_run('TST')
    assert pytest.approx(1.0, rel=1e-2) == res_beta['beta']
    # Volatility: std dev of returns. For linear series, returns constant -> volatility=0
    res_vol = await vol_run('TST')
    assert pytest.approx(0.0, abs=1e-6) == res_vol['volatility']

