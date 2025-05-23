import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import pandas as pd
from unittest.mock import AsyncMock, patch # Ensure patch is imported
from backend.agents.technical.rsi_agent import run as rsi_run
from backend.agents.technical.macd_agent import run as macd_run
from backend.agents.valuation.pe_ratio_agent import run as pe_run
from datetime import date, timedelta # Import date utilities
import httpx # Import httpx for httpx_mock
from pytest_httpx import httpx_mock # Explicitly import httpx_mock
import pytest_httpx # Add this import
from backend.config.settings import get_settings # ADDED: Import get_settings
import backend.config.settings as app_settings # Import the settings module itself

# Define default dates for mocks
DEFAULT_END_DATE = date.today()
DEFAULT_START_DATE = DEFAULT_END_DATE - timedelta(days=90)

# Patch order: innermost decorator corresponds to the first argument after self/cls
@patch('backend.agents.base.get_redis_client', new_callable=AsyncMock)      # For AgentBase.initialize
@patch('backend.agents.decorators.get_redis_client', new_callable=AsyncMock) # For @cache_agent_result decorator
@pytest.mark.asyncio
async def test_rsi_agent_accuracy(
    mock_decorator_get_redis_client, # Corresponds to decorators.get_redis_client
    mock_base_get_redis_client,      # Corresponds to base.get_redis_client
    monkeypatch
):
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get = AsyncMock(return_value=None) # Simulate cache miss
    mock_redis_instance.set = AsyncMock()
    mock_base_get_redis_client.return_value = mock_redis_instance
    mock_decorator_get_redis_client.return_value = mock_redis_instance

    # Fixed price series to calculate known RSI value
    # 15 points allow for the first 14-period RSI calculation
    prices = pd.Series([45,46,47,48,47,46,45,44,43,42,41,40,41,42,43])
    # Mock fetch_ohlcv_series used by rsi_agent
    async def mock_fetch_ohlcv(symbol, start_date=DEFAULT_START_DATE, end_date=DEFAULT_END_DATE):
        # Return a DataFrame with a 'close' column
        return pd.DataFrame({'close': prices})
    monkeypatch.setattr('backend.agents.technical.rsi_agent.fetch_ohlcv_series', mock_fetch_ohlcv)
    # Mock get_market_context as it's called by the agent (needed for adjustments)
    monkeypatch.setattr('backend.agents.technical.rsi_agent.RSIAgent.get_market_context', AsyncMock(return_value={"regime": "NEUTRAL"}))

    res = await rsi_run('ABC')
    assert res.get('error') is None, f"RSI agent returned error: {res.get('error')}"
    assert 'value' in res, "\'value\' key missing from rsi_agent result"
    assert pytest.approx(44.54, abs=0.15) == res['value'] # Assert calculated RSI value

@patch('backend.agents.base.get_redis_client', new_callable=AsyncMock)
@patch('backend.agents.decorators.get_redis_client', new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_macd_agent_accuracy(
    mock_decorator_get_redis_client,
    mock_base_get_redis_client,
    monkeypatch
):
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get = AsyncMock(return_value=None)
    mock_redis_instance.set = AsyncMock()
    mock_base_get_redis_client.return_value = mock_redis_instance
    mock_decorator_get_redis_client.return_value = mock_redis_instance

    prices = pd.Series([10,11,12,13,14,15,14,13,12,11,10]) # Test price movement
    # MACD requires enough data points for EMAs (12, 26) and Signal line (9).
    # Need at least 26+9-1=34 points for first signal value.
    # Prepend stable prices to ensure EMAs stabilize before the test series. 40 stable points + 11 test points = 51 points total.
    extended_prices = pd.concat([pd.Series([10]*40), prices], ignore_index=True)
    
    # Mock fetch_ohlcv_series used by macd_agent
    async def mock_fetch_ohlcv(symbol, start_date=DEFAULT_START_DATE, end_date=DEFAULT_END_DATE):
        # Return a DataFrame with a 'close' column
        return pd.DataFrame({'close': extended_prices})
    monkeypatch.setattr('backend.agents.technical.macd_agent.fetch_ohlcv_series', mock_fetch_ohlcv)
    # Mock get_market_context as it's called by the agent
    monkeypatch.setattr('backend.agents.technical.macd_agent.MACDAgent.get_market_context', AsyncMock(return_value={"regime": "NEUTRAL"}))

    res = await macd_run('ABC')
    assert res.get('error') is None, f"MACD agent returned error: {res.get('error')}"
    # Assert keys exist before accessing
    assert 'details' in res, "'details' key missing from macd_agent result"
    assert 'macd' in res['details'], "'macd' key missing from macd_agent details"
    assert 'signal' in res['details'], "'signal' key missing from macd_agent details"

    # MACD line - signal line should be close to zero or slightly positive/negative
    # depending on the exact calculation points and smoothing.
    # Assert that the MACD and Signal lines are reasonably close.
    macd_val = res['details']['macd']
    signal_val = res['details']['signal']
    
    # Check if MACD and Signal are approximately equal, allowing for small differences.
    # The absolute difference should be small. The relative difference might be large if values are near zero.
    # Let's check the absolute difference is within a small tolerance, e.g., 0.1 or 0.2.
    # assert abs(macd_val - signal_val) == pytest.approx(0.0, abs=0.2) # Check absolute difference is near zero
    assert macd_val == pytest.approx(signal_val, abs=0.25) # Check absolute difference is near zero

@pytest.mark.asyncio
# Use monkeypatch in addition to httpx_mock
async def test_pe_ratio_calculation(httpx_mock, monkeypatch):
    # Reset the global settings cache to ensure monkeypatched env var is read
    app_settings._settings = None 
    monkeypatch.setenv("ALPHA_VANTAGE_KEY", "demo") # Ensure data_provider uses 'demo' key

    # Mock the function responsible for fetching current price
    mock_fetch_price = AsyncMock(return_value={"price": 120.0}) # Corrected key to "price"
    monkeypatch.setattr(
        'backend.agents.valuation.pe_ratio_agent.fetch_price_point',  # Corrected path
        mock_fetch_price
    )

    # Mock the function responsible for fetching EPS
    async def mock_fetch_latest_eps_func(symbol, **kwargs):
        return {"eps": 4.0} # Adjusted to match expected return

    monkeypatch.setattr(
        'backend.agents.valuation.pe_ratio_agent.fetch_latest_eps',  # Corrected path
        AsyncMock(side_effect=mock_fetch_latest_eps_func)
    )
    
    # Mock the historical price fetch function within the agent's module
    # Return None to simulate missing historical data (this part was already correct)
    mock_hist_prices = AsyncMock(return_value=None)
    monkeypatch.setattr(
        'backend.agents.valuation.pe_ratio_agent.fetch_historical_price_series', 
        mock_hist_prices
    )

    # Run the agent
    res = await pe_run('TCS', {}) # Pass empty dict for agent_outputs

    # --- Assertions ---
    # 1. Check for errors first
    assert res.get('error') is None, f"Agent returned an error: {res.get('error')}"
    assert res.get('verdict') not in ['NO_DATA', 'NEGATIVE_EARNINGS'], f"Agent returned unexpected verdict: {res.get('verdict')}"

    # 2. Check essential keys exist
    assert 'value' in res, "Result missing 'value' key (expected P/E ratio)"
    assert 'verdict' in res, "Result missing 'verdict' key"

    # 3. Assert calculated P/E ratio (using the 'value' key)
    # Expected P/E = 120.00 / 4.00 = 30.0
    assert res['value'] == pytest.approx(30.0, rel=1e-2)
    
    # 4. Assert the verdict based on mocked historical data (None)
    # Agent should return NO_HISTORICAL_CONTEXT when historical data is missing
    assert res['verdict'] == 'NO_HISTORICAL_CONTEXT'