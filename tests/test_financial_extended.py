import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import pytest
import pandas as pd
# Ensure patch is imported, and MagicMock if complex mock objects are needed
from unittest.mock import AsyncMock, patch, MagicMock
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

@patch('backend.data.providers.unified_provider.UnifiedDataProvider', new_callable=AsyncMock) # Outermost, now AsyncMock
@patch('backend.agents.base.get_redis_client', new_callable=AsyncMock) # Middle
@patch('backend.agents.decorators.get_redis_client', new_callable=AsyncMock) # Innermost
@pytest.mark.asyncio
async def test_rsi_agent_precision(
    mock_decorator_redis,    # Corresponds to innermost @patch('...decorators.get_redis_client')
    mock_base_redis,         # Corresponds to middle @patch('...base.get_redis_client')
    MockUnifiedDataProvider, # Corresponds to outermost @patch('...UnifiedDataProvider')
    monkeypatch
):
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get = AsyncMock(return_value=None)
    mock_redis_instance.set = AsyncMock()
    mock_base_redis.return_value = mock_redis_instance
    mock_decorator_redis.return_value = mock_redis_instance

    # Setup mock for DataProvider (used by Agent's __init__)
    mock_dp_instance = AsyncMock()
    # This get_ohlcv might not be directly called if MarketContext is fully managed by the new mock,
    # but it's good for the completeness of the UnifiedDataProvider mock.
    prices_for_dp = pd.Series(list(range(1, 31))) 
    ohlcv_df_for_dp = pd.DataFrame({'close': prices_for_dp})
    mock_dp_instance.get_ohlcv = AsyncMock(return_value=ohlcv_df_for_dp)
    MockUnifiedDataProvider.return_value = mock_dp_instance
    
    # Create a mock MarketContext instance
    mock_market_context_instance = AsyncMock()

    # Setup data for get_price_data (called by agent's run_calculation)
    prices_for_agent = pd.Series(list(range(1, 31))) # 30 periods of gains
    mock_market_context_instance.get_price_data = AsyncMock(return_value=prices_for_agent)

    # Setup data for get_regime (called by agent's run_calculation)
    mock_market_context_instance.get_regime = AsyncMock(return_value="NEUTRAL")

    # Patch RSIAgent.get_market_context to return the mock_market_context_instance
    monkeypatch.setattr(
        'backend.agents.technical.rsi_agent.RSIAgent.get_market_context',
        AsyncMock(return_value=mock_market_context_instance)
    )

    res = await rsi_run('TST')
    assert res.get('error') is None, f"RSI agent returned error: {res.get('error')}"
    assert 'value' in res, "'value' key (containing RSI) missing from rsi_agent result"
    assert pytest.approx(100.0, rel=1e-2) == res['value']

@patch('backend.data.providers.unified_provider.UnifiedDataProvider', new_callable=AsyncMock) # Outermost, now AsyncMock
@patch('backend.agents.base.get_redis_client', new_callable=AsyncMock) # Middle
@patch('backend.agents.decorators.get_redis_client', new_callable=AsyncMock) # Innermost
@pytest.mark.asyncio
async def test_macd_agent_precision(
    mock_decorator_redis,    # Corresponds to innermost @patch('...decorators.get_redis_client')
    mock_base_redis,         # Corresponds to middle @patch('...base.get_redis_client')
    MockUnifiedDataProvider, # Corresponds to outermost @patch('...UnifiedDataProvider')
    monkeypatch
):
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get = AsyncMock(return_value=None)
    mock_redis_instance.set = AsyncMock()
    mock_base_redis.return_value = mock_redis_instance
    mock_decorator_redis.return_value = mock_redis_instance

    # Setup mock for DataProvider (used by Agent's __init__)
    mock_dp_instance = AsyncMock()
    prices_for_dp = pd.Series([i for i in range(1,30)])
    ohlcv_df_for_dp = pd.DataFrame({'close': prices_for_dp})
    mock_dp_instance.get_ohlcv = AsyncMock(return_value=ohlcv_df_for_dp)
    MockUnifiedDataProvider.return_value = mock_dp_instance

    # Create a mock MarketContext instance
    mock_market_context_instance = AsyncMock()

    # Setup data for get_price_data (called by agent's run_calculation)
    prices_for_agent = pd.Series([i for i in range(1,30)])
    mock_market_context_instance.get_price_data = AsyncMock(return_value=prices_for_agent)
    
    # Setup data for get_regime (called by agent's run_calculation)
    mock_market_context_instance.get_regime = AsyncMock(return_value="NEUTRAL")
    
    # Patch MACDAgent.get_market_context to return the mock_market_context_instance
    monkeypatch.setattr(
        'backend.agents.technical.macd_agent.MACDAgent.get_market_context',
        AsyncMock(return_value=mock_market_context_instance)
    )
    
    res = await macd_run('TST')
    assert res.get('error') is None, f"MACD agent returned error: {res.get('error')}"
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
    assert pytest.approx(426.79, abs=0.15) == res_vol['value']

