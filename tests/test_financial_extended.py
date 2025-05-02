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
from datetime import date, timedelta # Import date utilities

# Define default dates for mocks
DEFAULT_END_DATE = date.today()
DEFAULT_START_DATE = DEFAULT_END_DATE - timedelta(days=90)

@pytest.mark.asyncio
async def test_rsi_agent_precision(monkeypatch):
    # Up series for RSI=100 exactly (need at least 14 periods of gains)
    prices = pd.Series(list(range(1, 31))) # 30 periods of gains
    # Patch fetch_ohlcv_series as that's what rsi_agent uses
    async def mock_fetch_ohlcv(symbol, start_date=DEFAULT_START_DATE, end_date=DEFAULT_END_DATE):
        # Return a DataFrame with a 'close' column
        return pd.DataFrame({'close': prices})
    monkeypatch.setattr('backend.agents.technical.rsi_agent.fetch_ohlcv_series', mock_fetch_ohlcv)
    # Mock get_market_context as it's called by the agent
    monkeypatch.setattr('backend.agents.technical.rsi_agent.RSIAgent.get_market_context', AsyncMock(return_value={"regime": "NEUTRAL"}))

    res = await rsi_run('TST')
    # Assert the primary 'value' field which contains the RSI
    assert 'value' in res, "'value' key (containing RSI) missing from rsi_agent result"
    # With only gains, RSI should be 100
    assert pytest.approx(100.0, rel=1e-2) == res['value']

@pytest.mark.asyncio
async def test_macd_agent_precision(monkeypatch):
    prices = pd.Series([i for i in range(1,30)])
    # Patch fetch_ohlcv_series as that's what macd_agent uses
    async def mock_fetch_ohlcv(symbol, start_date=DEFAULT_START_DATE, end_date=DEFAULT_END_DATE):
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
    # For a steadily increasing series, MACD should be positive and generally above signal
    assert macd_val > 0
    # Corrected comparison: Direct comparison should work for this scenario
    assert macd_val >= signal_val

@pytest.mark.asyncio
async def test_beta_and_volatility(monkeypatch):
    # Mock data
    symbol_prices = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], name="Close")
    market_prices = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], name="Close") # Perfect correlation

    # Mock fetch_price_series using AsyncMock
    async def mock_fetch(sym, *args, **kwargs):
        # Need settings for market index symbol inside the mock
        from backend.config.settings import get_settings
        if sym == 'TST':
            return symbol_prices
        elif sym == get_settings().data_provider.MARKET_INDEX_SYMBOL: # Use actual setting
            return market_prices
        else:
            return pd.Series([]) # Return empty for other symbols

    # Patch fetch_price_series where it's used by beta_agent and vol_run
    mock_fetch_async = AsyncMock(side_effect=mock_fetch)
    monkeypatch.setattr('backend.agents.risk.beta_agent.fetch_price_series', mock_fetch_async)
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
    # For linear series [1..10], simple returns are [1.0, 0.5, 0.33...], std dev is not 0.
    # Calculated annualized volatility % is ~426.79
    # assert pytest.approx(0.0, abs=1e-4) == res_vol['value'] # Original assertion was incorrect
    assert pytest.approx(426.79, abs=0.1) == res_vol['value']

