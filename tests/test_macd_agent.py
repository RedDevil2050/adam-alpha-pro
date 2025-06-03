import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import pandas as pd
import numpy as np
import datetime
from unittest.mock import AsyncMock, patch, MagicMock, ANY # Ensure ANY is imported
from backend.agents.technical.macd_agent import MACDAgent, run as macd_run, agent_name
from backend.config.settings import AgentSettings

@pytest.mark.asyncio
@patch('backend.config.settings.AgentSettings')
@patch('backend.market.context.MarketContext.get_instance')
@patch('backend.agents.base.get_redis_client', new_callable=AsyncMock)
@patch('backend.agents.decorators.get_redis_client', new_callable=AsyncMock)
@patch('backend.agents.technical.macd_agent.datetime')
@patch.object(MACDAgent, 'get_market_context', new_callable=AsyncMock)
@patch('pandas.core.window.ewm.ExponentialMovingWindow.mean')
@patch('backend.data.providers.unified_provider.UnifiedDataProvider') # Ensure no autospec=True
async def test_macd_agent_buy_signal(
    mock_unified_data_provider_class,
    mock_ewm_mean,
    mock_agent_get_market_context,
    mock_datetime_in_agent,
    mock_decorator_get_redis_client,
    mock_base_get_redis_client,
    mock_market_context_get_instance,
    mock_agent_settings_class,
    monkeypatch
):
    # --- Mock MarketContext.get_instance() for the decorator ---
    mock_mcp_instance_for_decorator = AsyncMock()
    mock_market_context_get_instance.return_value = mock_mcp_instance_for_decorator

    # --- Mock AgentSettings ---
    mock_settings_instance = MagicMock(spec=AgentSettings)
    mock_settings_instance.agent_name = agent_name
    mock_settings_instance.agent_cache_enabled = True
    mock_settings_instance.agent_cache_ttl_seconds = 3600
    mock_settings_instance.agent_cache_db_index = 0
    mock_settings_instance.macd_short_period = 12
    mock_settings_instance.macd_long_period = 26
    mock_settings_instance.macd_signal_period = 9
    def get_setting_side_effect(key, default=None):
        return getattr(mock_settings_instance, key, default)
    mock_settings_instance.get_setting = MagicMock(side_effect=get_setting_side_effect)
    mock_agent_settings_class.return_value = mock_settings_instance

    # --- Mock Configuration ---
    symbol = "TEST_SYMBOL"
    market_regime = "BULL"
    real_datetime_date_class = datetime.date
    real_datetime_timedelta_class = datetime.timedelta
    mock_today_date_object = real_datetime_date_class(2025, 5, 2)
    mock_datetime_in_agent.date.today.return_value = mock_today_date_object
    mock_datetime_in_agent.timedelta = real_datetime_timedelta_class
    mock_datetime_in_agent.datetime = datetime.datetime

    # --- Mock DataProvider ---
    data_df = pd.DataFrame({'close': np.linspace(100, 110, 35)})
    mock_dp_instance = AsyncMock()
    mock_dp_instance.fetch_price_data = AsyncMock(return_value=data_df) # MODIFIED
    mock_unified_data_provider_class.return_value = mock_dp_instance

    # --- Mock EWM ---
    mock_exp1_series = pd.Series([11.5])
    mock_exp2_series = pd.Series([10.0])
    mock_signal_series = pd.Series([1.0])
    mock_ewm_mean.side_effect = [mock_exp1_series, mock_exp2_series, mock_signal_series]

    # --- Mock Agent's get_market_context ---
    mock_agent_get_market_context.return_value = {"regime": market_regime}

    # --- Mock Redis ---
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get = AsyncMock(return_value=None)
    mock_redis_instance.set = AsyncMock()
    mock_decorator_get_redis_client.return_value = mock_redis_instance
    mock_base_get_redis_client.return_value = mock_redis_instance

    # --- Expected Calculations ---
    expected_verdict = "BUY"
    expected_macd_value = 1.5
    expected_signal_value = 1.0
    expected_hist_value = 0.5

    # --- Run Agent ---
    result = await macd_run(symbol)

    # --- Assertions ---
    assert result['symbol'] == symbol
    assert result['agent_name'] == agent_name 
    assert result.get('error') is None, f"Agent returned error: {result.get('error')}"
    assert result['verdict'] == expected_verdict
    assert result['confidence'] > 0.5 
    assert result['value'] == pytest.approx(expected_macd_value) 
    details = result['details']
    assert details['macd'] == pytest.approx(expected_macd_value)
    assert details['signal'] == pytest.approx(expected_signal_value)
    assert details['histogram'] == pytest.approx(expected_hist_value)
    assert details['market_regime'] == market_regime

    # --- Verify Mocks ---
    # Using ANY for dates as exact object matching can be tricky with datetime manipulations
    mock_dp_instance.fetch_price_data.assert_awaited_once_with(
        symbol,
        start_date=ANY, 
        end_date=ANY,
        interval='1d' # MODIFIED: Ensure interval is checked
    )
    assert mock_ewm_mean.call_count == 3
    mock_agent_get_market_context.assert_awaited_once_with(symbol)
    mock_base_get_redis_client.assert_awaited_once()      
    assert mock_redis_instance.get.await_count == 1 
    if result.get('verdict') not in ['NO_DATA', 'ERROR', None]:
        assert mock_redis_instance.set.await_count == 1 
    else:
        mock_redis_instance.set.assert_not_awaited()

@pytest.mark.asyncio
@patch('backend.data.providers.unified_provider.UnifiedDataProvider') # Ensure no autospec=True
@patch('backend.market.context.MarketContext.get_instance')
@patch('backend.agents.base.get_redis_client', new_callable=AsyncMock)
@patch('backend.agents.decorators.get_redis_client', new_callable=AsyncMock)
async def test_macd_agent_schema(
    mock_decorator_get_redis_client,
    mock_base_get_redis_client,
    mock_market_context_get_instance,
    mock_unified_data_provider_class,
    monkeypatch
):
    symbol = "INFY"

    # --- Mock MarketContext.get_instance() for the decorator ---
    mock_mcp_instance_for_decorator = AsyncMock()
    mock_market_context_get_instance.return_value = mock_mcp_instance_for_decorator

    # --- Mock Redis ---
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get = AsyncMock(return_value=None)
    mock_redis_instance.set = AsyncMock()
    mock_decorator_get_redis_client.return_value = mock_redis_instance
    mock_base_get_redis_client.return_value = mock_redis_instance

    # --- Mock DataProvider ---
    mock_data_df = pd.DataFrame({'close': [100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126] * 2})
    
    explicit_mock_dp_instance = AsyncMock()
    explicit_mock_dp_instance.fetch_price_data = AsyncMock(return_value=mock_data_df) # MODIFIED
    
    fallback_mock_dp_instance = AsyncMock()
    fallback_mock_dp_instance.fetch_price_data = AsyncMock(return_value=mock_data_df) # MODIFIED
    mock_unified_data_provider_class.return_value = fallback_mock_dp_instance


    with patch.object(MACDAgent, 'get_market_context', new_callable=AsyncMock) as mock_agent_get_market_context, \
         patch('backend.agents.technical.macd_agent.datetime') as mock_datetime_in_agent:
        
        real_datetime_date_class = datetime.date
        mock_today_date_object = real_datetime_date_class(2025, 5, 2)
        mock_datetime_in_agent.date.today.return_value = mock_today_date_object
        mock_datetime_in_agent.timedelta = datetime.timedelta

        mock_agent_get_market_context.return_value = {"regime": "NEUTRAL"}
        
        result = await macd_run(symbol, data_provider=explicit_mock_dp_instance)

        assert result is not None
        assert isinstance(result, dict)
        assert result.get('error') is None, f"Agent returned error: {result.get('error')}"
        assert "symbol" in result
        assert "verdict" in result
        assert "confidence" in result
        assert "value" in result
        assert "details" in result
        assert "agent_name" in result
        assert result["verdict"] in {"BUY", "SELL", "HOLD", "NO_DATA", "ERROR"}
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

    # Explicitly verify that the passed data_provider's get_ohlcv was called
    explicit_mock_dp_instance.fetch_price_data.assert_awaited_once_with(
        symbol,
        start_date=mock.ANY, # Start date is calculated based on REQUIRED_HISTORY_DAYS
        end_date=mock.ANY,   # End date is the mocked today's date
    )

    # Fallback mock should not have been called if the explicit one was used
    mock_unified_data_provider_class.return_value.fetch_price_data.assert_not_awaited()
