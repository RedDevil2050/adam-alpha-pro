import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import pytest
import pandas as pd
from unittest.mock import AsyncMock
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
    # Mock data
    symbol_prices = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], name="Close")
    market_prices = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], name="Close") # Perfect correlation

    # Mock fetch_price_series using AsyncMock
    async def mock_fetch(sym, *args, **kwargs):
        if sym == 'TST':
            return symbol_prices
        elif sym == get_settings().data_provider.MARKET_INDEX_SYMBOL: # Use actual setting
            return market_prices
        else:
            return pd.Series([]) # Return empty for other symbols

    # Need settings for market index symbol
    from backend.config.settings import get_settings
    # Patch fetch_price_series where it's used by beta_agent and vol_run
    # Assuming both import it directly from data_provider
    # If they import differently, adjust the target accordingly
    mock_fetch_async = AsyncMock(side_effect=mock_fetch)
    monkeypatch.setattr('backend.agents.risk.beta_agent.fetch_price_series', mock_fetch_async)
    # Also patch for volatility agent if it uses the same function
    monkeypatch.setattr('backend.agents.risk.volatility_level_agent.fetch_price_series', mock_fetch_async)

    # Run agents
    res_beta = await beta_run('TST')
    # Check for error first, or assert key exists
    assert 'error' not in res_beta, f"Beta agent returned error: {res_beta.get('error')}"
    assert 'beta' in res_beta, "'beta' key missing from beta_agent result"
    assert pytest.approx(1.0, rel=1e-2) == res_beta['beta']

    # Volatility agent also uses fetch_price_series, mock is already set
    res_vol = await vol_run('TST')
    assert 'error' not in res_vol, f"Volatility agent returned error: {res_vol.get('error')}"
    assert 'volatility' in res_vol, "'volatility' key missing from vol_run result"
    # For linear series, returns are constant (except first NaN), std dev should be 0
    assert pytest.approx(0.0, abs=1e-6) == res_vol['volatility']

