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
    # Patch fetch_ohlcv_series as that's what rsi_agent uses
    async def mock_fetch_ohlcv(symbol):
        # Return a DataFrame with a 'close' column
        return pd.DataFrame({'close': prices})
    monkeypatch.setattr('backend.agents.technical.rsi_agent.fetch_ohlcv_series', mock_fetch_ohlcv)
    # Mock get_market_context as it's called by the agent
    monkeypatch.setattr('backend.agents.technical.rsi_agent.RSIAgent.get_market_context', AsyncMock(return_value={"regime": "NEUTRAL"}))
    
    res = await rsi_run('TST')
    # Assert the primary 'value' field which contains the RSI
    assert 'value' in res, "'value' key (containing RSI) missing from rsi_agent result"
    assert pytest.approx(100.0, rel=1e-2) == res['value']

@pytest.mark.asyncio
async def test_macd_agent_precision(monkeypatch):
    prices = pd.Series([i for i in range(1,30)])
    # Patch fetch_ohlcv_series as that's what macd_agent uses
    async def mock_fetch_ohlcv(symbol):
        # Return a DataFrame with a 'close' column
        return pd.DataFrame({'close': prices})
    monkeypatch.setattr('backend.agents.technical.macd_agent.fetch_ohlcv_series', mock_fetch_ohlcv)
    # Mock get_market_context as it's called by the agent
    monkeypatch.setattr('backend.agents.technical.macd_agent.MACDAgent.get_market_context', AsyncMock(return_value={"regime": "NEUTRAL"}))

    res = await macd_run('TST')
    # Check for errors first
    assert 'error' not in res or res['error'] is None, f"MACD agent returned error: {res.get('error')}"
    # Assert keys exist before accessing
    assert 'details' in res, "'details' key missing from macd_agent result"
    assert 'macd' in res['details'], "'macd' key missing from macd_agent details"
    assert 'signal' in res['details'], "'signal' key missing from macd_agent details"
    
    # Compare macd and signal from the details dictionary
    macd_val = res['details']['macd']
    signal_val = res['details']['signal']
    assert pytest.approx(macd_val, rel=0.1) == signal_val or macd_val > signal_val

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
    assert 'error' not in res_beta or res_beta['error'] is None, f"Beta agent returned error: {res_beta.get('error')}"
    # Assert the primary 'value' field for beta
    assert 'value' in res_beta, "'value' key (containing beta) missing from beta_agent result"
    assert pytest.approx(1.0, rel=1e-2) == res_beta['value']

    # Volatility agent also uses fetch_price_series, mock is already set
    res_vol = await vol_run('TST')
    assert 'error' not in res_vol or res_vol['error'] is None, f"Volatility agent returned error: {res_vol.get('error')}"
    # Assert the primary 'value' field for volatility
    assert 'value' in res_vol, "'value' key (containing volatility) missing from vol_run result"
    # For linear series, returns are constant (except first NaN), std dev should be 0
    # The agent returns annualized volatility percentage
    assert pytest.approx(0.0, abs=1e-4) == res_vol['value']

