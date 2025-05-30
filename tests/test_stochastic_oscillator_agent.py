\
# filepath: d:\\\\Zion\\\\tests\\\\test_stochastic_oscillator_agent.py
import pytest
import asyncio
import pandas as pd
import numpy as np
import json
from datetime import datetime, date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

# Imports from the module to be tested
from backend.agents.technical.stochastic_oscillator_agent import (
    StochasticOscillatorAgent,
    AGENT_NAME
)
from backend.models.common_models import VerdictType, MarketRegime
from backend.config.settings import AgentSettings # For type hinting
from backend.data.providers.base_provider import BaseDataProvider # For type hinting

# If StochasticOscillatorSettings were a separate Pydantic model, it would be imported here.
# The agent accesses self.settings.stochastic_oscillator, assuming it's an attribute (dict or model).

@pytest.fixture
def mock_logger():
    logger = MagicMock()
    logger.debug = MagicMock()
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    logger.critical = MagicMock()
    return logger

@pytest.fixture
def mock_cache_client():
    client = AsyncMock()
    client.get = AsyncMock(return_value=None)  # Default to cache miss
    client.set = AsyncMock()
    return client

@pytest.fixture
def mock_data_provider():
    provider = AsyncMock(spec=BaseDataProvider)
    provider.fetch_ohlcv_series = AsyncMock()
    return provider

@pytest.fixture
def mock_market_context_provider():
    provider = AsyncMock() # spec=BaseMarketContextProvider if defined
    provider.get_market_context = AsyncMock(return_value={
        "regime": MarketRegime.NEUTRAL.value,  # Default
        "volatility_factor": 1.0,
    })
    return provider

@pytest.fixture
def mock_agent_settings():
    settings = MagicMock(spec=AgentSettings)
    settings.agent_cache_enabled = True
    settings.agent_cache_ttl_seconds = 3600
    
    stoch_settings = MagicMock()
    stoch_settings.get = MagicMock() 

    stoch_settings_dict = {
        "oversold_threshold": 20,
        "overbought_threshold": 80,
        "bull_market_oversold_adjustment": 5,
        "bear_market_oversold_adjustment": -5,
        "volatility_threshold_sensitivity": 0.2,
        "bull_market_bullish_signal_boost": 0.1,
        "bull_market_bearish_signal_dampen_factor": 0.8,
        "bear_market_bearish_signal_boost": 0.1, # This makes sell signal stronger (closer to 0)
        "bear_market_bullish_signal_dampen_factor": 0.8
    }
    stoch_settings.get.side_effect = lambda key, default=None: stoch_settings_dict.get(key, default)

    for k, v in stoch_settings_dict.items():
        setattr(stoch_settings, k, v) # Allow attribute access too
        
    settings.stochastic_oscillator = stoch_settings
    return settings

def create_ohlcv_df(rows, k_period=14): # k_period is not used here, but kept for signature
    if rows <= 0:
        return pd.DataFrame(columns=['high', 'low', 'close', 'open', 'volume'])

    timestamps = [datetime(2023, 1, 1) + timedelta(days=i) for i in range(rows)]
    
    # Start with a base price and let it evolve
    prices = [100.0] # Initial base price
    for _ in range(1, rows):
        # Generate a price change, encouraging some movement
        change = np.random.normal(loc=0.05, scale=1.5) # Small positive drift, reasonable volatility
        prices.append(max(10.0, prices[-1] + change)) # Ensure price > 0 (e.g., min 10)

    close_prices = np.array(prices)
    
    # Determine high and low relative to close, ensuring a spread
    # High prices: close + random positive offset
    high_offsets = np.random.uniform(0.5, 3.0, size=rows) # High is at least 0.5 to 3.0 units above close
    high_prices = close_prices + high_offsets
    
    # Low prices: close - random positive offset
    low_offsets = np.random.uniform(0.5, 3.0, size=rows)  # Low is at least 0.5 to 3.0 units below close
    low_prices = close_prices - low_offsets
    
    # Ensure low < high, and ideally low <= close <= high.
    # By construction, low_prices < close_prices < high_prices if offsets are positive.
    # Just in case, ensure low is strictly less than high.
    low_prices = np.minimum(low_prices, high_prices - 0.1) # Ensure low is at least 0.1 below high

    # Generate open prices
    open_prices = np.zeros(rows)
    if rows > 0:
        open_prices[0] = close_prices[0] - np.random.uniform(0.1, 0.5) # First open slightly below first close
        if rows > 1:
            open_prices[1:] = close_prices[:-1] # Subsequent opens are the previous close

    # Ensure open prices are within the day's low and high
    open_prices = np.maximum(low_prices, np.minimum(high_prices, open_prices))
    
    # Ensure close prices are also within the day's low and high after open is set
    # (This might adjust close if open pushed boundaries, though less likely with this setup)
    close_prices_final = np.maximum(low_prices, np.minimum(high_prices, close_prices))


    volumes = np.random.randint(1000, 10000, size=rows)

    df = pd.DataFrame({
        'timestamp': timestamps,
        'open': open_prices,
        'high': high_prices,
        'low': low_prices,
        'close': close_prices_final, # Use adjusted close
        'volume': volumes
    })
    df = df.set_index('timestamp')
    return df

# Removed class-level @pytest.mark.asyncio
class TestStochasticOscillatorAgent:
    fixed_now_for_tests = datetime(2023, 7, 15, 12, 0, 0)

    @pytest.fixture(autouse=True)
    def _patch_datetime_now(self, monkeypatch):
        datetime_mock = MagicMock(wraps=datetime)
        datetime_mock.now.return_value = self.fixed_now_for_tests
        # Patch datetime in AgentBase as well, as it's used for timestamps
        monkeypatch.setattr("backend.agents.base.datetime", datetime_mock)
        monkeypatch.setattr("backend.agents.technical.stochastic_oscillator_agent.datetime", datetime_mock)

    @pytest.mark.asyncio # Added to individual test
    async def test_agent_initialization(self, mock_agent_settings, mock_logger, mock_cache_client, mock_data_provider, mock_market_context_provider):
        # Test initialization via the constructor as AgentBase now expects arguments
        agent = StochasticOscillatorAgent(
            name=AGENT_NAME,
            settings=mock_agent_settings,
            logger=mock_logger,
            cache_client=mock_cache_client,
            data_provider=mock_data_provider,
            market_context_provider=mock_market_context_provider
        )
        assert agent.name == AGENT_NAME
        assert agent.settings == mock_agent_settings
        assert agent.logger == mock_logger
        assert agent.cache_client == mock_cache_client
        assert agent.data_provider == mock_data_provider
        assert agent.market_context_provider == mock_market_context_provider
        mock_logger.debug.assert_called_with(f"Agent {AGENT_NAME} v{agent.version} initialized.")

    # Removed @pytest.mark.no_asyncio
    def test_generate_cache_key(self, mock_agent_settings, mock_logger, mock_cache_client, mock_data_provider, mock_market_context_provider):
        agent = StochasticOscillatorAgent(
            name=AGENT_NAME,
            settings=mock_agent_settings,
            logger=mock_logger,
            cache_client=mock_cache_client,
            data_provider=mock_data_provider,
            market_context_provider=mock_market_context_provider
        )
        # The _generate_cache_key in AgentBase now takes symbol, agent_outputs, and **kwargs
        # The agent_outputs are part of the key, and k_period etc. are kwargs
        key = agent._generate_cache_key("SYM", {"some_output": "value"}, k_period=14, d_period=3, smoothing=3)
        
        # Construct the expected key based on AgentBase._generate_cache_key logic
        expected_key_components = [
            agent.agent_type, # "technical" (from TechnicalAgentBase -> StochasticOscillatorAgent)
            "SYM",
            json.dumps({"some_output": "value"}, sort_keys=True),
            json.dumps({"k_period":14, "d_period":3, "smoothing":3}, sort_keys=True)
        ]
        expected_key = ":".join(expected_key_components)
        assert key == expected_key

    @pytest.mark.asyncio # Added to individual test
    @patch.object(StochasticOscillatorAgent, 'get_market_context', new_callable=AsyncMock)
    async def test_execute_happy_path_structure(self, mock_get_market_context, mock_agent_settings, mock_logger, mock_cache_client, mock_data_provider, mock_market_context_provider):
        agent = StochasticOscillatorAgent(
            name=AGENT_NAME, settings=mock_agent_settings, logger=mock_logger,
            cache_client=mock_cache_client, data_provider=mock_data_provider,
            market_context_provider=mock_market_context_provider # This will be patched
        )
        mock_data_provider.fetch_ohlcv_series.return_value = create_ohlcv_df(rows=40)
        
        mock_get_market_context.return_value = {"regime": MarketRegime.NEUTRAL.value, "volatility_factor": 1.0}
        
        # Call public execute
        result = await agent.execute("TESTSYM", agent_outputs={}, k_period=14, d_period=3, smoothing=3)
        
        assert "verdict" in result
        assert result["verdict"] in [v.value for v in VerdictType] # Check against VerdictType values
        assert "confidence" in result and 0.0 <= result["confidence"] <= 1.0
        assert "timestamp" in result 
        assert result["agent_name"] == AGENT_NAME
        assert result["agent_version"] == agent.version
        assert result["symbol"] == "TESTSYM"
        assert "details" in result 
        # Check details from _execute, which are nested under 'details' by _format_output
        details_from_execute = result["details"]
        assert all(k in details_from_execute for k in ["k", "d", "prev_k", "prev_d", "oversold_threshold_used", "overbought_threshold_used", "market_regime_detected"])
        assert "retrieved_from_cache" in result and result["retrieved_from_cache"] is False


    @pytest.mark.asyncio # Added to individual test
    @patch.object(StochasticOscillatorAgent, 'get_market_context', new_callable=AsyncMock)
    async def test_execute_bull_market_regime_adjusts_thresholds(self, mock_get_market_context, mock_agent_settings, mock_logger, mock_cache_client, mock_data_provider, mock_market_context_provider):
        agent = StochasticOscillatorAgent(
            name=AGENT_NAME, settings=mock_agent_settings, logger=mock_logger,
            cache_client=mock_cache_client, data_provider=mock_data_provider,
            market_context_provider=mock_market_context_provider # This will be patched
        )
        mock_data_provider.fetch_ohlcv_series.return_value = create_ohlcv_df(rows=40)
        
        mock_get_market_context.return_value = {"regime": MarketRegime.BULL.value, "volatility_factor": 1.0}

        base_oversold = mock_agent_settings.stochastic_oscillator.get("oversold_threshold")
        bull_adj = mock_agent_settings.stochastic_oscillator.get("bull_market_oversold_adjustment")
        expected_oversold = max(5.0, min(40.0, base_oversold + bull_adj))

        result = await agent.execute("SYM_BULL", agent_outputs={}, k_period=14, d_period=3, smoothing=3)
        
        details_from_execute = result["details"]
        mock_get_market_context.assert_called_once_with("SYM_BULL")
        assert details_from_execute['market_regime_detected'] == MarketRegime.BULL.value.upper()
        assert details_from_execute['oversold_threshold_used'] == pytest.approx(expected_oversold)
        assert details_from_execute['overbought_threshold_used'] == pytest.approx(mock_agent_settings.stochastic_oscillator.get("overbought_threshold"))


    @pytest.mark.asyncio # Added to individual test
    @patch.object(StochasticOscillatorAgent, 'get_market_context', new_callable=AsyncMock)
    async def test_execute_bear_market_regime_adjusts_thresholds(self, mock_get_market_context, mock_agent_settings, mock_logger, mock_cache_client, mock_data_provider, mock_market_context_provider):
        agent = StochasticOscillatorAgent(
            name=AGENT_NAME, settings=mock_agent_settings, logger=mock_logger,
            cache_client=mock_cache_client, data_provider=mock_data_provider,
            market_context_provider=mock_market_context_provider # This will be patched
        )
        mock_data_provider.fetch_ohlcv_series.return_value = create_ohlcv_df(rows=40)
        mock_get_market_context.return_value = {"regime": MarketRegime.BEAR.value, "volatility_factor": 1.0}

        base_oversold = mock_agent_settings.stochastic_oscillator.get("oversold_threshold")
        bear_adj = mock_agent_settings.stochastic_oscillator.get("bear_market_oversold_adjustment")
        expected_oversold_after_adj = base_oversold + bear_adj
        expected_oversold_clamped = max(5.0, min(40.0, expected_oversold_after_adj))

        result = await agent.execute("SYM_BEAR", agent_outputs={}, k_period=14, d_period=3, smoothing=3)
        details_from_execute = result["details"]
        mock_get_market_context.assert_called_once_with("SYM_BEAR")
        assert details_from_execute['market_regime_detected'] == MarketRegime.BEAR.value.upper()
        assert details_from_execute['oversold_threshold_used'] == pytest.approx(expected_oversold_clamped)
        assert details_from_execute['overbought_threshold_used'] == pytest.approx(mock_agent_settings.stochastic_oscillator.get("overbought_threshold"))

    @pytest.mark.asyncio # Added to individual test
    @patch.object(StochasticOscillatorAgent, 'get_market_context', new_callable=AsyncMock)
    async def test_execute_threshold_clamping(self, mock_get_market_context, mock_agent_settings, mock_logger, mock_cache_client, mock_data_provider, mock_market_context_provider):
        agent = StochasticOscillatorAgent(
            name=AGENT_NAME, settings=mock_agent_settings, logger=mock_logger,
            cache_client=mock_cache_client, data_provider=mock_data_provider,
            market_context_provider=mock_market_context_provider # This will be patched
        )
        mock_data_provider.fetch_ohlcv_series.return_value = create_ohlcv_df(rows=40)
        
        original_stoch_settings_get = mock_agent_settings.stochastic_oscillator.get

        # Test case 1
        mock_agent_settings.stochastic_oscillator.get = MagicMock(side_effect=lambda key, default=None: {
            "oversold_threshold": 70, "overbought_threshold": 25,
            "bull_market_oversold_adjustment": 0, "bear_market_oversold_adjustment": 0,
            "volatility_threshold_sensitivity": 0.0
        }.get(key, default))
        
        mock_get_market_context.return_value = {"regime": MarketRegime.NEUTRAL.value, "volatility_factor": 1.0}
        
        result1 = await agent.execute("SYM_CLAMP1", agent_outputs={}, k_period=14, d_period=3, smoothing=3)
        mock_get_market_context.assert_called_once_with("SYM_CLAMP1")
        assert result1['details']['oversold_threshold_used'] == 40.0
        assert result1['details']['overbought_threshold_used'] == 60.0

        # Test case 2
        mock_agent_settings.stochastic_oscillator.get = MagicMock(side_effect=lambda key, default=None: {
            "oversold_threshold": 35, "overbought_threshold": 65,
            "bull_market_oversold_adjustment": 10, "bear_market_oversold_adjustment": -10,
            "volatility_threshold_sensitivity": 0.0
        }.get(key, default))
        
        mock_get_market_context.reset_mock() # Reset for this case
        mock_get_market_context.return_value = {"regime": MarketRegime.BULL.value, "volatility_factor": 1.0}

        result2 = await agent.execute("SYM_CLAMP2_BULL", agent_outputs={}, k_period=14, d_period=3, smoothing=3)
        mock_get_market_context.assert_called_once_with("SYM_CLAMP2_BULL")
        assert result2['details']['oversold_threshold_used'] == 40.0 # 35 + 10 = 45, clamped to 40
        assert result2['details']['overbought_threshold_used'] == 65.0
        
        # Restore original mock
        mock_agent_settings.stochastic_oscillator.get = original_stoch_settings_get


    @pytest.mark.asyncio # Added to individual test
    @patch.object(StochasticOscillatorAgent, 'get_market_context', new_callable=AsyncMock)
    async def test_execute_full_flow_cache_miss_and_hit(self, mock_get_market_context, mock_agent_settings, mock_logger, mock_cache_client, mock_data_provider, mock_market_context_provider):
        # Configure mock_agent_settings for caching
        mock_agent_settings.agent_cache_enabled = True
        mock_agent_settings.agent_cache_ttl = 3600  # Set a default TTL

        agent = StochasticOscillatorAgent(
            name=AGENT_NAME, settings=mock_agent_settings, logger=mock_logger,
            cache_client=mock_cache_client, data_provider=mock_data_provider,
            market_context_provider=mock_market_context_provider # This will be patched
        )
        symbol = "AAPL"
        params = {"k_period": 14, "d_period": 3, "smoothing": 3}
        agent_outputs_param = {"some_data": "value"}

        # Cache Miss
        mock_cache_client.get.return_value = None 
        mock_data_provider.fetch_ohlcv_series.return_value = create_ohlcv_df(rows=40)
        
        mock_get_market_context.return_value = {"regime": MarketRegime.NEUTRAL.value, "volatility_factor": 1.0}

        result_miss = await agent.execute(symbol, agent_outputs=agent_outputs_param, **params)
        
        mock_get_market_context.assert_called_once_with(symbol)
        mock_cache_client.set.assert_called_once()
        
        args_set, kwargs_set = mock_cache_client.set.call_args
        cached_key_str = args_set[0]
        cached_value_str = args_set[1] 
        
        # Reset mocks for the cache hit scenario
        mock_data_provider.fetch_ohlcv_series.reset_mock()
        mock_cache_client.get.return_value = cached_value_str 
        mock_get_market_context.reset_mock() # Reset the mock for get_market_context

        result_hit = await agent.execute(symbol, agent_outputs=agent_outputs_param, **params)
        
        mock_get_market_context.assert_not_called() # Should not be called on cache hit
        mock_cache_client.get.assert_called_with(cached_key_str) 
        mock_data_provider.fetch_ohlcv_series.assert_not_called() 
        assert result_hit["retrieved_from_cache"] is True


# Removed test_run_function_instantiates_and_calls_agent as the 'run' function is obsolete.
# @pytest.mark.asyncio
# async def test_run_function_instantiates_and_calls_agent(
#     mock_agent_settings, mock_data_provider, mock_cache_client,
#     mock_logger, mock_market_context_provider
# ):
#     symbol = "MSFT"
#     agent_outputs_param = {"prev_data": "some_value"}
#     k, d, s = 10, 2, 1
# 
#     expected_result_from_execute = {"verdict": VerdictType.HOLD_NEUTRAL.value, "confidence": 0.5, "details": {}}
# 
#     # Patch the class in the module where it's used by `run_agent`
#     with patch('backend.agents.technical.stochastic_oscillator_agent.StochasticOscillatorAgent', autospec=True) as MockAgentClass:
#         mock_agent_instance = MockAgentClass.return_value 
#         mock_agent_instance.execute = AsyncMock(return_value=expected_result_from_execute)
#         
#         # `run_agent` is expected to instantiate the agent and call execute.
#         actual_result = await run_agent(
#             symbol=symbol, 
#             agent_outputs=agent_outputs_param, 
#             settings=mock_agent_settings,
#             data_provider=mock_data_provider, 
#             cache_client=mock_cache_client,
#             logger_instance=mock_logger, 
#             market_context_provider=mock_market_context_provider,
#             k_period=k, d_period=d, smoothing=s
#         )
# 
#         # Assert that StochasticOscillatorAgent was called with the correct arguments by run_agent
#         MockAgentClass.assert_called_once_with(
#             name=AGENT_NAME, # run_agent should pass the AGENT_NAME
#             settings=mock_agent_settings,
#             logger=mock_logger,
#             cache_client=mock_cache_client,
#             data_provider=mock_data_provider,
#             market_context_provider=mock_market_context_provider
#         )
# 
#         # Assert that the execute method on the instance was called correctly
#         mock_agent_instance.execute.assert_called_once_with(
#             symbol=symbol,
#             agent_outputs=agent_outputs_param,
#             k_period=k,
#             d_period=d,
#             smoothing=s
#         )
#         
#         assert actual_result == expected_result_from_execute

# More tests for specific crossover logic, confidence adjustments, etc. can be added.
# For example:
# - test_bullish_crossover_oversold
# - test_bearish_crossover_overbought
# - test_confidence_adjustment_bull_market_bull_signal
# - test_confidence_adjustment_bear_market_sell_signal
# These would involve crafting specific data for df_copy['k_series'] and df_copy['d_series']
# and mocking get_market_context to control regime and volatility.
