import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


from unittest.mock import AsyncMock, patch, MagicMock
import pandas as pd
import pytest
from pytest_httpx import HTTPXMock # Added import

from backend.agents.technical.rsi_agent import run as rsi_agent_run, RSIAgent
from backend.agents.technical.macd_agent import run as macd_agent_run, MACDAgent
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

# Patch the UnifiedDataProvider where it's instantiated by the standard_agent_execution decorator
@patch('backend.agents.decorators.UnifiedDataProvider') 
@patch('backend.agents.technical.rsi_agent.RSIAgent.get_market_context', new_callable=AsyncMock)
async def test_rsi_agent_precision(
    mock_get_market_context, 
    mock_unified_data_provider_class, # This is now the class mock
    httpx_mock: HTTPXMock, 
    sample_real_stock_data,
    monkeypatch # Added monkeypatch
):
    # Redis mock setup
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get = AsyncMock(return_value=None)
    mock_redis_instance.set = AsyncMock()
    mock_base_redis.return_value = mock_redis_instance
    mock_decorator_redis.return_value = mock_redis_instance

    # Setup for UnifiedDataProvider instance mock
    # Configure the instance that will be returned by the mocked class
    mock_dp_instance = AsyncMock()
    mock_dp_instance.get_ohlcv = AsyncMock(return_value=ohlcv_df)
    mock_unified_data_provider_class.return_value = mock_dp_instance
    
    mock_get_market_context.return_value = {"regime": "NEUTRAL"}

    # Mock Redis if necessary (assuming AgentSettings enables caching)
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get = AsyncMock(return_value=None) # Cache miss
    mock_redis_instance.set = AsyncMock()
    
    # Patch get_redis_client for AgentBase and decorators
    monkeypatch.setattr('backend.agents.base.get_redis_client', AsyncMock(return_value=mock_redis_instance))
    monkeypatch.setattr('backend.agents.decorators.get_redis_client', AsyncMock(return_value=mock_redis_instance))

    agent_result = await rsi_agent_run(symbol="TEST_REAL_STOCK")

    # Assertions
    assert agent_result.get('error_code') is None, f"RSI agent returned error: {agent_result.get('error_message', agent_result.get('error'))} with code {agent_result.get('error_code')}"
    assert 'details' in agent_result, "'details' key missing from rsi_agent result"
    assert 'value' in agent_result['details'], f"'value' key (containing RSI) missing from rsi_agent details. Result: {agent_result}"
    assert isinstance(agent_result['details']['value'], float), f"RSI value is not a float. Got: {type(agent_result['details']['value'])}"
    assert 0 <= agent_result['details']['value'] <= 100, f"RSI value out of bounds (0-100). Got: {agent_result['details']['value']}"


@patch('backend.agents.decorators.UnifiedDataProvider')
@patch('backend.agents.technical.macd_agent.MACDAgent.get_market_context', new_callable=AsyncMock)
async def test_macd_agent_precision(
    mock_get_market_context, 
    mock_unified_data_provider_class, # This is now the class mock
    httpx_mock: HTTPXMock, 
    sample_real_stock_data,
    monkeypatch # Added monkeypatch
):
    # Redis mock setup
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get = AsyncMock(return_value=None)
    mock_redis_instance.set = AsyncMock()
    mock_base_redis.return_value = mock_redis_instance
    mock_decorator_redis.return_value = mock_redis_instance

    # Setup for UnifiedDataProvider instance mock
    # Configure the instance that will be returned by the mocked class
    mock_dp_instance = AsyncMock()
    mock_dp_instance.get_ohlcv = AsyncMock(return_value=ohlcv_df)
    mock_unified_data_provider_class.return_value = mock_dp_instance
    
    mock_get_market_context.return_value = {"regime": "NEUTRAL"}

    # Mock Redis if necessary
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get = AsyncMock(return_value=None) # Cache miss
    mock_redis_instance.set = AsyncMock()

    monkeypatch.setattr('backend.agents.base.get_redis_client', AsyncMock(return_value=mock_redis_instance))
    monkeypatch.setattr('backend.agents.decorators.get_redis_client', AsyncMock(return_value=mock_redis_instance))

    agent_result = await macd_agent_run(symbol="TEST_REAL_STOCK")

    # Assertions
    assert agent_result.get('error_code') is None, f"MACD agent returned error: {agent_result.get('error_message', agent_result.get('error'))} with code {agent_result.get('error_code')}"
    assert 'details' in agent_result, "'details' key missing from macd_agent result"
    assert 'macd' in agent_result['details'], f"'macd' key missing from macd_agent details. Result: {agent_result}"
    assert 'signal' in agent_result['details'], f"'signal' key missing from macd_agent details. Result: {agent_result}"
    assert 'histogram' in agent_result['details'], f"'histogram' key missing from macd_agent details. Result: {agent_result}"
    assert isinstance(agent_result['details']['macd'], float), "MACD value is not a float"
    assert isinstance(agent_result['details']['signal'], float), "Signal value is not a float"
    assert isinstance(agent_result['details']['histogram'], float), "Histogram value is not a float"

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
    assert pytest.approx(426.79, abs=0.15) == res_vol['value']

