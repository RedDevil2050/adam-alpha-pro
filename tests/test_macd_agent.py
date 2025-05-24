import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import pandas as pd
import numpy as np
import datetime
from unittest.mock import AsyncMock, patch, MagicMock
from backend.agents.technical.macd_agent import run as macd_run, MACDAgent # Import run and the class

agent_name = "macd_agent"

@pytest.mark.asyncio
@patch('backend.agents.base.get_redis_client', new_callable=AsyncMock)      # For AgentBase.initialize
@patch('backend.agents.decorators.get_redis_client', new_callable=AsyncMock) # For @cache_agent_result decorator
# Patch dependencies (innermost first)
# Patch datetime used by the agent (for datetime.date.today(), timedelta, etc.)
@patch('backend.agents.technical.macd_agent.datetime')
# Patch the get_market_context method directly on the class prototype
@patch.object(MACDAgent, 'get_market_context')
# Patch the data fetching function used by the agent
@patch('backend.agents.technical.macd_agent.fetch_ohlcv_series')
# Patch the pandas EWM calculation
@patch('pandas.core.window.ewm.ExponentialMovingWindow.mean')
async def test_macd_agent_buy_signal(
    mock_decorator_get_redis_client, # Added for @cache_agent_result
    mock_base_get_redis_client,      # Added for AgentBase
    mock_ewm_mean,
    mock_fetch_ohlcv,
    mock_get_market_context,
    mock_datetime_in_agent # This is the mock for 'backend.agents.technical.macd_agent.datetime'
):
    # --- Mock Configuration ---
    symbol = "TEST_SYMBOL"
    market_regime = "BULL"
    
    # Use real datetime for test setup, but mock what the agent sees
    real_datetime_date_class = datetime.date
    real_datetime_timedelta_class = datetime.timedelta

    mock_today_date_object = real_datetime_date_class(2025, 5, 2)

    # Configure datetime.date.today() as seen by the agent
    # The agent calls datetime.date.today()
    mock_datetime_in_agent.date.today.return_value = mock_today_date_object

    # Ensure timedelta and datetime.datetime are available if the agent uses them via the mocked datetime module
    mock_datetime_in_agent.timedelta = real_datetime_timedelta_class
    # If agent uses datetime.datetime.strptime or other datetime.datetime methods:
    mock_datetime_in_agent.datetime = datetime.datetime 

    # 1. Mock fetch_ohlcv_series
    # Create a dummy DataFrame with a 'close' column
    data_df = pd.DataFrame({'close': np.linspace(100, 110, 35)}) # Need enough data for EWM
    mock_fetch_ohlcv.return_value = data_df

    # 2. Mock EWM calculations to produce BUY signal
    # We need macd > signal and histogram > 0
    # Let macd = 1.5, signal = 1.0 => histogram = 0.5
    # Let exp1.iloc[-1] = 11.5
    # Let exp2.iloc[-1] = 10.0 => macd = 1.5
    # Let signal_calc_input = macd (which is exp1 - exp2)
    # Let signal_calc_output.iloc[-1] = 1.0 => hist = 0.5

    # Return actual pd.Series with the desired final value
    # The agent code performs subtraction on the Series, then uses iloc[-1]
    mock_exp1_series = pd.Series([11.5]) # Series with the final value
    mock_exp2_series = pd.Series([10.0]) # Series with the final value
    # The signal line calculation takes the macd series as input
    # Mock the result of the signal line's .mean() call
    mock_signal_series = pd.Series([1.0]) # Series with the final signal value

    # The order matters: exp1, exp2, signal
    mock_ewm_mean.side_effect = [mock_exp1_series, mock_exp2_series, mock_signal_series]

    # 3. Mock get_market_context
    mock_get_market_context.return_value = {"regime": market_regime}

    # Configure Redis Mocks (shared instance)
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get = AsyncMock(return_value=None) # Simulate cache miss
    mock_redis_instance.set = AsyncMock()
    mock_decorator_get_redis_client.return_value = mock_redis_instance
    mock_base_get_redis_client.return_value = mock_redis_instance

    # --- Expected Calculations ---
    # Based on mocked means: macd = 11.5 - 10.0 = 1.5, signal = 1.0, hist = 0.5
    # Since macd > signal and hist > 0 => verdict = BUY
    # Base confidence = 0.8
    # Confidence adjusted for BULL regime (assuming adjust_for_market_regime increases it)
    # We will assert confidence > 0.5 without mocking the adjustment function itself.
    expected_verdict = "BUY"
    expected_macd_value = 1.5
    expected_signal_value = 1.0
    expected_hist_value = 0.5

    # --- Run Agent ---
    # The run function creates an instance, so patching the class method works.
    result = await macd_run(symbol)

    # --- Assertions ---
    assert result['symbol'] == symbol
    assert result['agent_name'] == agent_name # Corrected to use the module-level agent_name
    assert result['verdict'] == expected_verdict
    # Check confidence was adjusted (likely > base 0.5 for HOLD)
    assert result['confidence'] > 0.5 
    assert result['value'] == pytest.approx(expected_macd_value) # Value is current_macd
    assert result.get('error') is None, f"Agent returned error: {result.get('error')}"

    # Check details
    assert 'details' in result
    details = result['details']
    assert details['macd'] == pytest.approx(expected_macd_value)
    assert details['signal'] == pytest.approx(expected_signal_value)
    assert details['histogram'] == pytest.approx(expected_hist_value)
    assert details['market_regime'] == market_regime

    # --- Verify Mocks ---
    # Calculate expected dates based on the mocked today's date
    end_date = mock_today_date_object # Use the object used for mocking
    start_date = end_date - real_datetime_timedelta_class(days=365) # Use real timedelta for test calculation
    mock_fetch_ohlcv.assert_awaited_once_with(symbol, start_date=start_date, end_date=end_date)
    # Check ewm().mean() calls
    assert mock_ewm_mean.call_count == 3
    # iloc[-1] is called *after* subtraction in the agent code, so we don't verify it on the mocks directly.
    # Instead, we rely on the assertions on the final 'result' dictionary.
    mock_get_market_context.assert_awaited_once_with(symbol)
    mock_decorator_get_redis_client.assert_awaited_once() # Verify decorator Redis mock
    mock_base_get_redis_client.assert_awaited_once()      # Verify base Redis mock
    assert mock_redis_instance.get.await_count >= 1 # Decorator might call get, base will call get
    if result.get('verdict') not in ['NO_DATA', 'ERROR', None]:
        assert mock_redis_instance.set.await_count >= 1 # Decorator might call set, base will call set

@pytest.mark.asyncio
@patch('backend.agents.base.get_redis_client', new_callable=AsyncMock)      # For AgentBase.initialize
@patch('backend.agents.decorators.get_redis_client', new_callable=AsyncMock) # For @cache_agent_result decorator
async def test_macd_agent_schema(mock_decorator_get_redis_client, mock_base_get_redis_client):
    symbol = "INFY"

    # Configure Redis Mocks
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get = AsyncMock(return_value=None)
    mock_redis_instance.set = AsyncMock()
    mock_decorator_get_redis_client.return_value = mock_redis_instance
    mock_base_get_redis_client.return_value = mock_redis_instance

    # Mock dependencies for schema test to avoid actual calculation/fetching
    with patch('backend.agents.technical.macd_agent.fetch_ohlcv_series', new_callable=AsyncMock) as mock_fetch, \
         patch.object(MACDAgent, 'get_market_context', new_callable=AsyncMock) as mock_context:
        
        # Provide minimal valid return values for mocks
        mock_fetch.return_value = pd.DataFrame({'close': [100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126]}) # Ensure enough data
        mock_context.return_value = {"regime": "NEUTRAL"}

        result = await macd_run(symbol)

    assert isinstance(result, dict)
    assert result.get('error') is None, f"Agent returned error: {result.get('error')}"
    assert "symbol" in result
    assert "verdict" in result
    assert "confidence" in result
    assert "value" in result
    assert "details" in result
    assert "agent_name" in result
    # Correct possible verdicts based on agent code
    assert result["verdict"] in {"BUY", "SELL", "HOLD", "NO_DATA", "ERROR"} 
    # Correct confidence range based on agent code (0.0 to 1.0)
    assert 0.0 <= result["confidence"] <= 1.0 
    if result["value"] is not None and result["verdict"] not in {"NO_DATA", "ERROR"}:
        assert isinstance(result["value"], (int, float))
    # Ensure details is a dict if verdict is not ERROR/NO_DATA
    if result["verdict"] not in {"NO_DATA", "ERROR"}:
        assert isinstance(result["details"], dict)
        assert "macd" in result["details"]
        assert "signal" in result["details"]
        assert "histogram" in result["details"]
        assert "market_regime" in result["details"]
