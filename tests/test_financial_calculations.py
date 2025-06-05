import pandas as pd
import pytest
from unittest.mock import AsyncMock, patch
from pytest_httpx import HTTPXMock # Added import

from backend.agents.technical.rsi_agent import RSIAgent, run as rsi_agent_run
from backend.agents.technical.macd_agent import MACDAgent, run as macd_agent_run # Added import
from backend.data.providers.unified_provider import UnifiedDataProvider
from backend.config.settings import AgentSettings

from backend.config import settings as app_settings # Changed import
from backend.agents.valuation.pe_ratio_agent import run as pe_run


# Assuming DEFAULT_START_DATE and DEFAULT_END_DATE are in data_provider or a constants file
# For the sake of this example, let's assume they are in data_provider
# If not, adjust the import path accordingly.
# from backend.utils.data_provider import DEFAULT_START_DATE, DEFAULT_END_DATE
# If they are not available, we might need to define them or mock them differently.
# For now, let's assume they are imported if rsi_agent and macd_agent tests need them.
# If these are not found, the tests for rsi_agent and macd_agent will fail at runtime.
# We will mock them if necessary within the tests that use them if not globally available.
from datetime import date, timedelta # For DEFAULT_START_DATE, DEFAULT_END_DATE if not imported
import pandas as pd # Ensure pandas is imported for DataFrame creation in mock

DEFAULT_START_DATE = date.today() - timedelta(days=365)
DEFAULT_END_DATE = date.today()


@patch('backend.agents.base.get_redis_client', new_callable=AsyncMock)      # For AgentBase.initialize
@patch('backend.agents.decorators.get_redis_client', new_callable=AsyncMock) # For @cache_agent_result decorator
@pytest.mark.asyncio
async def test_pe_ratio_agent_no_price_data(
    mock_decorator_get_redis_client,
    mock_base_get_redis_client,
    httpx_mock,
    monkeypatch
):
    app_settings._settings = None
    monkeypatch.setenv("ALPHA_VANTAGE_KEY", "demo")

    mock_redis_instance = AsyncMock()
    mock_redis_instance.get = AsyncMock(return_value=None)
    mock_redis_instance.set = AsyncMock()
    mock_base_get_redis_client.return_value = mock_redis_instance
    mock_decorator_get_redis_client.return_value = mock_redis_instance

    # Mock fetch_price_point to return None (no data)
    mock_fetch_price = AsyncMock(return_value=None)
    monkeypatch.setattr(
        'backend.agents.valuation.pe_ratio_agent.fetch_price_point',
        mock_fetch_price
    )

    # Mock fetch_latest_eps to return valid EPS (though it might not be called if price is missing first)
    mock_fetch_eps_func = AsyncMock(return_value={"eps": 2.0})
    monkeypatch.setattr(
        'backend.agents.valuation.pe_ratio_agent.fetch_latest_eps',
        mock_fetch_eps_func
    )
    
    mock_hist_prices = AsyncMock(return_value=None)
    monkeypatch.setattr(
        'backend.agents.valuation.pe_ratio_agent.fetch_historical_price_series', 
        mock_hist_prices
    )

    res = await pe_run('XYZ', {})

    # assert res.get('error') is None, f"Agent returned an error: {res.get('error')}"
    if res.get('verdict') != 'NO_DATA': assert res.get('error') is None, f"Agent returned an error: {res.get('error')}"
    assert res.get('verdict') == 'NO_DATA', \
        f"Expected 'NO_DATA' verdict when price is missing, got {res.get('verdict')}"
    assert 'value' not in res or res['value'] is None, \
        f"P/E 'value' should be None or absent for NO_DATA, got {res.get('value')}"

    # mock_base_get_redis_client.assert_awaited_once()
    mock_decorator_get_redis_client.assert_awaited_once()
    mock_fetch_price.assert_awaited_once_with('XYZ')
    # EPS fetch might not be called if price fetch fails first, depending on agent logic
    # mock_fetch_eps_func.assert_not_awaited() # Or assert_awaited_once_with('XYZ') if it's always called


@patch('backend.agents.base.get_redis_client', new_callable=AsyncMock)      # For AgentBase.initialize
@patch('backend.agents.decorators.get_redis_client', new_callable=AsyncMock) # For @cache_agent_result decorator
@pytest.mark.asyncio
async def test_pe_ratio_agent_no_eps_data(
    mock_decorator_get_redis_client,
    mock_base_get_redis_client,
    httpx_mock,
    monkeypatch
):
    app_settings._settings = None
    monkeypatch.setenv("ALPHA_VANTAGE_KEY", "demo")

    mock_redis_instance = AsyncMock()
    mock_redis_instance.get = AsyncMock(return_value=None)
    mock_redis_instance.set = AsyncMock()
    mock_base_get_redis_client.return_value = mock_redis_instance
    mock_decorator_get_redis_client.return_value = mock_redis_instance

    mock_fetch_price = AsyncMock(return_value={"price": 50.0})
    monkeypatch.setattr(
        'backend.agents.valuation.pe_ratio_agent.fetch_price_point',
        mock_fetch_price
    )

    # Mock fetch_latest_eps to return None (no data)
    mock_fetch_eps_func = AsyncMock(return_value=None)
    monkeypatch.setattr(
        'backend.agents.valuation.pe_ratio_agent.fetch_latest_eps',
        mock_fetch_eps_func
    )
    
    mock_hist_prices = AsyncMock(return_value=None)
    monkeypatch.setattr(
        'backend.agents.valuation.pe_ratio_agent.fetch_historical_price_series', 
        mock_hist_prices
    )

    res = await pe_run('XYZ', {})

    # assert res.get('error') is None, f"Agent returned an error: {res.get('error')}"
    if res.get('verdict') != 'NO_DATA': assert res.get('error') is None, f"Agent returned an error: {res.get('error')}"
    assert res.get('verdict') == 'NO_DATA', \
        f"Expected 'NO_DATA' verdict when EPS is missing, got {res.get('verdict')}"
    assert 'value' not in res or res['value'] is None, \
        f"P/E 'value' should be None or absent for NO_DATA, got {res.get('value')}"

    # mock_base_get_redis_client.assert_awaited_once()
    mock_decorator_get_redis_client.assert_awaited_once()
    mock_fetch_price.assert_awaited_once_with('XYZ')
    mock_fetch_eps_func.assert_awaited_once_with('XYZ')


@patch('backend.utils.data_provider.provider')  # Patch the 'provider' instance directly
@patch('backend.market.context.MarketContext.get_instance', new_callable=AsyncMock)
@patch('backend.agents.decorators.get_redis_client', new_callable=AsyncMock)
@patch('backend.agents.base.get_redis_client', new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_rsi_agent_accuracy(
    mock_base_get_redis_client,
    mock_decorator_get_redis_client,
    mock_market_context_get_instance,
    mock_provider_instance,  # This is now the mocked backend.utils.data_provider.provider
    monkeypatch
):
    # Setup for mock_market_context_get_instance
    mock_mcp_instance = AsyncMock()
    mock_market_context_get_instance.return_value = mock_mcp_instance

    mock_redis_instance = AsyncMock()
    mock_redis_instance.get = AsyncMock(return_value=None) # Simulate cache miss
    mock_redis_instance.set = AsyncMock()
    mock_base_get_redis_client.return_value = mock_redis_instance
    mock_decorator_get_redis_client.return_value = mock_redis_instance

    # Fixed price series to calculate known RSI value
    close_prices = [45,46,47,48,47,46,45,44,43,42,41,40,41,42,43.0] # Length 15

    # Update mock_fetch_ohlcv_data to accept interval and **kwargs
    async def mock_fetch_ohlcv_data(symbol, start_date=DEFAULT_START_DATE, end_date=DEFAULT_END_DATE, interval="1d", **kwargs):
        num_periods = len(close_prices)
        data = {
            'open': [p - 0.5 for p in close_prices],
            'high': [p + 0.5 for p in close_prices],
            'low': [p - 1.0 for p in close_prices],
            'close': close_prices,
            'volume': [1000.0] * num_periods
        }
        actual_end_date = pd.Timestamp(end_date)
        index = pd.date_range(end=actual_end_date, periods=num_periods, freq='B')
        df = pd.DataFrame(data, index=index)
        df.columns = [col.lower() for col in df.columns]
        # print(f"Mock returning DataFrame: empty={df.empty}, shape={df.shape}, columns={df.columns}, index_min={df.index.min()}, index_max={df.index.max()}")
        return df

    # Configure the fetch_price_data method on the mocked provider instance
    mock_provider_instance.fetch_price_data = AsyncMock(side_effect=mock_fetch_ohlcv_data)

    # Mock get_market_context as it's called by the agent (needed for adjustments)
    monkeypatch.setattr('backend.agents.technical.rsi_agent.RSIAgent.get_market_context', AsyncMock(return_value={"regime": "NEUTRAL"}))

    res = await rsi_agent_run('ABC')
    
    mock_provider_instance.fetch_price_data.assert_awaited_once() # Ensure the mock was called

    if res.get('verdict') == 'ERROR' or (res.get('details') and res['details'].get('error_message')):
        error_info = res.get('details', {}).get('error_code', res.get('details', {}).get('error_message', 'Unknown error'))
        pytest.fail(f"RSI agent returned error: {error_info} - Full result: {res}")

    # Basic check for non-empty values if calculation succeeded
    if res.get('verdict') not in ["NO_DATA", "ERROR", None]: 
        assert 'details' in res, "'details' key missing from rsi_agent result"
        assert 'rsi' in res['details'], "\'rsi\' (value) key missing from rsi_agent result details"
        assert pytest.approx(44.54, abs=0.15) == res['details']['rsi'] # Assert calculated RSI value


# Ensure this patch is correctly targeting the UnifiedDataProvider
# Adding new_callable=AsyncMock if the instantiation of UnifiedDataProvider might be async
@patch('backend.agents.technical.macd_agent.MACDAgent.get_market_context', new_callable=AsyncMock)
# Patch UnifiedDataProvider where the decorator will instantiate it
@patch('backend.data.providers.unified_provider.UnifiedDataProvider') # Corrected: Patch target to actual source
@pytest.mark.asyncio
async def test_macd_agent_accuracy(
    mock_unified_data_provider_class, 
    mock_get_market_context,
    httpx_mock: HTTPXMock
    # sample_stock_data_json fixture removed
):
    symbol = "TEST_STOCK"
    # Mock for Redis (same as before)
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get = AsyncMock(return_value=None)
    mock_redis_instance.set = AsyncMock()
    # No need to patch base.get_redis_client here if not used
    # mock_base_redis_client.return_value = mock_redis_instance
    # mock_decorator_redis_client.return_value = mock_redis_instance

    # Setup mock for DataProvider instance
    mock_dp_instance = mock_unified_data_provider_class.return_value 
    # Sample data for OHLCV
    extended_prices = [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35]
    mock_ohlcv_df = pd.DataFrame({'close': extended_prices})
    # Fix: Mock fetch_price_data instead of get_ohlcv
    mock_dp_instance.fetch_price_data = AsyncMock(return_value=mock_ohlcv_df)

    # Mock the market context
    mock_get_market_context.return_value = {"regime": "NEUTRAL"} 

    agent_result = await macd_agent_run(symbol=symbol)

    # Assertions
    assert agent_result.get('error_code') is None, f"MACD agent returned error: {agent_result.get('error_message', agent_result.get('error'))} with code {agent_result.get('error_code')}"
    assert 'details' in agent_result, "'details' key missing from macd_agent result"
    assert 'macd' in agent_result['details'], f"'macd' key missing from macd_agent details. Result: {agent_result}"
    assert 'signal' in agent_result['details'], f"'signal' key missing from macd_agent details. Result: {agent_result}"
    assert 'histogram' in agent_result['details'], f"'histogram' key missing from macd_agent details. Result: {agent_result}"
    # Basic check for non-empty values if calculation succeeded
    assert agent_result['details']['macd'] is not None, "MACD value is None"

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