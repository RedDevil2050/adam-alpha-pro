import asyncio
import datetime
from unittest.mock import AsyncMock, MagicMock, patch, ANY # Added ANY
import pytest

# Assuming these are the correct paths for your project structure
from backend.agents.technical.stochastic_oscillator_agent import StochasticOscillatorAgent as OriginalStochasticOscillatorAgent, run as actual_stoch_run_decorated_function # Changed stoch_run to run
from backend.models import TimeSeriesData, DataPoint, Verdict, Context, AgentSettings # Corrected import path
from backend.models import VerdictType, MarketRegime 
from backend.data.providers.base_provider import BaseDataProvider as DataProviderBase # Corrected import for DataProviderBase

original_agent_module_name = OriginalStochasticOscillatorAgent.name

# Dummy helper function for creating test data - replace with your actual data generation if needed
async def create_stochastic_data(symbol, num_points, scenario, k_p, s_k, d_p):
    # Simplified: returns a list of DataPoint objects
    # In a real scenario, this would generate data based on the 'scenario' (oversold, overbought, etc.)
    return TimeSeriesData(data=[
        DataPoint(timestamp=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=i),
                  open_price=100+i, high_price=105+i, low_price=95+i, close_price=100+i, volume=1000)
        for i in range(num_points)
    ])

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "test_id, k_p, d_p, s_k, market_regime_mock, data_scenario, expected_verdict_val, min_k, max_k, min_d, max_d, min_confidence_val",
    [
        ("oversold_bull", 14, 3, 3, "BULL", "oversold_buy", "BUY_OVERSOLD_CROSS", 5, 25, 5, 25, 0.8),
        ("oversold_neutral", 14, 3, 3, "NEUTRAL", "oversold_buy", "BUY_OVERSOLD_CROSS", 5, 25, 5, 25, 0.7),
        ("oversold_bear", 14, 3, 3, "BEAR", "oversold_buy", "BUY_OVERSOLD_CROSS", 5, 25, 5, 25, 0.6),
        ("overbought_bull", 14, 3, 3, "BULL", "overbought_sell", "SELL_OVERBOUGHT_CROSS", 75, 95, 75, 95, 0.15),
        ("overbought_neutral", 14, 3, 3, "NEUTRAL", "overbought_sell", "SELL_OVERBOUGHT_CROSS", 75, 95, 75, 95, 0.09),
        ("overbought_bear", 20, 5, 5, "BEAR", "overbought_sell", "SELL_OVERBOUGHT_CROSS", 75, 95, 75, 95, 0.0),
        ("neutral_hold", 14, 3, 3, "NEUTRAL", "neutral", "HOLD_NEUTRAL", 30, 70, 30, 70, 0.45),
    ]
)
@patch('backend.agents.technical.stochastic_oscillator_agent.timedelta', new=datetime.timedelta)
@patch('backend.agents.technical.stochastic_oscillator_agent.datetime')
# Patch the class used by stoch_run to instantiate the agent
@patch('backend.agents.technical.stochastic_oscillator_agent.StochasticOscillatorAgent') 
@patch('backend.agents.base.get_redis_client', new_callable=AsyncMock) # For AgentBase.cache_client
@patch('backend.agents.decorators.get_redis_client', new_callable=AsyncMock) # For @standard_agent_execution
@patch('backend.agents.decorators.get_tracker') # For @standard_agent_execution
async def test_stochastic_oscillator_scenarios(
    mock_decorator_tracker,
    mock_decorator_redis, 
    mock_base_redis,      
    mock_agent_class_factory, # This is the patched StochasticOscillatorAgent class
    mock_datetime_module_in_agent,
    test_id, k_p, d_p, s_k, market_regime_mock, data_scenario, expected_verdict_val, min_k, max_k, min_d, max_d, min_confidence_val
):
    symbol = f"TEST_STOCH_{test_id.upper()}"
    agent_internal_required_for_calc = (k_p - 1) + (s_k - 1) + (d_p - 1) + 2
    # Increased buffer slightly for safety, ensure create_stochastic_data provides enough points
    num_data_points_for_create = agent_internal_required_for_calc + 10 

    # --- Configure Mocks for Redis --- 
    async def mock_redis_get_side_effect(*args, **kwargs):
        # print(f"Redis GET called with {args}, {kwargs}. Returning None (cache miss).")
        return None # Simulate cache miss

    mock_redis_instance = AsyncMock(name=f"mock_redis_instance_{test_id}")
    mock_redis_instance.get = AsyncMock(name=f"mock_redis_instance.get_{test_id}", side_effect=mock_redis_get_side_effect)
    mock_redis_instance.set = AsyncMock(name=f"mock_redis_instance.set_{test_id}")
    # Add other Redis methods if used by the decorator or agent (e.g., hgetall, exists)
    # mock_redis_instance.exists = AsyncMock(return_value=0)

    # The get_redis_client mocks (used by decorator and base class) should return this instance
    mock_decorator_redis.return_value = mock_redis_instance
    mock_base_redis.return_value = mock_redis_instance

    # --- Configure Mock Agent Instance --- 
    # This is the instance that mock_agent_class_factory will return
    mock_agent_instance = MagicMock(spec=OriginalStochasticOscillatorAgent) 
    mock_agent_instance.name = original_agent_module_name
    mock_agent_instance._cache_client = None # Internal state for the property

    # Setup agent settings (ensure this matches AgentSettings structure if it's a class)
    agent_settings = AgentSettings(
        agent_name=original_agent_module_name,
        agent_cache_enabled=True, 
        agent_cache_ttl_seconds=3600,
        agent_cache_db_index=0,
        agent_data_lookback_period=num_data_points_for_create # Ensure lookback matches data
    )
    mock_agent_instance.settings = agent_settings

    # Configure the cache_client property behavior for mock_agent_instance
    async def cache_client_property_logic():
        # print("cache_client_property_logic called")
        if not mock_agent_instance.settings.agent_cache_enabled:
            # print("Cache disabled, property returns None")
            return None
        if mock_agent_instance._cache_client is None:
            # print("Initializing agent's _cache_client using mock_base_redis")
            mock_agent_instance._cache_client = await mock_base_redis(
                db_index=mock_agent_instance.settings.agent_cache_db_index,
                decode_responses=True
            )
            # print(f"Agent's _cache_client set to: {mock_agent_instance._cache_client}")
        return mock_agent_instance._cache_client

    # mock_agent_instance.cache_client is an async property. 
    # So, it should be an AsyncMock whose side_effect is an AWAITABLE.
    mock_agent_instance.cache_client = AsyncMock(name=f'custom_cache_client_prop_{test_id}', side_effect=cache_client_property_logic)
    # If the above await on mock_agent_instance.cache_client returns the mock itself,
    # then agent's cache_client_instance.get will be mock_agent_instance.cache_client.get.
    # Configure this child mock to return None when called and awaited.
    async def get_method_for_prop_mock(*args, **kwargs):
        return None
    mock_agent_instance.cache_client.get = get_method_for_prop_mock
    # The result of `await mock_agent_instance.cache_client` should ideally be `mock_redis_instance`
    # due to cache_client_property_logic. If it is, then `mock_redis_instance.get` (which returns None) will be used.
    # This change primarily addresses the scenario where `await mock_agent_instance.cache_client`
    # might unexpectedly return the property mock itself.

    # Configure the factory to return our fully configured mock_agent_instance
    mock_agent_class_factory.return_value = mock_agent_instance

    # --- Mock DataProvider and MCPClient --- 
    mock_dp_instance = AsyncMock(spec=DataProviderBase)
    ohlcv_data = await create_stochastic_data(symbol, num_data_points_for_create, data_scenario, k_p, s_k, d_p)
    mock_dp_instance.fetch_ohlcv_series.return_value = ohlcv_data

    mock_mcp_instance = AsyncMock(spec=Context) # Use your actual Context class if different
    mock_mcp_instance.get_context.return_value = {"market_regime": MarketRegime[market_regime_mock]}

    # --- Mock Agent's Internal Calculation and Verdict Generation --- 
    # These are methods of the *actual* agent logic that stoch_run will call on the instance it creates.
    # Since stoch_run gets mock_agent_instance, we configure these on mock_agent_instance.
    mock_agent_instance._calculate_stochastic_oscillator = AsyncMock(return_value=(float(min_k), float(min_d)))
    
    async def mock_generate_verdict_side_effect(k_value, d_value, market_regime_from_mcp):
        # This function is called by the agent's internal logic.
        # print(f"_generate_verdict called with k={k_value}, d={d_value}, regime={market_regime_from_mcp}")
        # Ensure the verdict_type matches the expected enum member
        return Verdict(
            agent_name=original_agent_module_name, 
            verdict_type=VerdictType[expected_verdict_val], 
            confidence=min_confidence_val, 
            details={ 'k': k_value, 'd': d_value, 'market_regime': market_regime_from_mcp.value if isinstance(market_regime_from_mcp, MarketRegime) else market_regime_from_mcp }
        )
    mock_agent_instance._generate_verdict = AsyncMock(side_effect=mock_generate_verdict_side_effect)

    # --- Execute Agent Logic via stoch_run --- 
    # actual_stoch_run_decorated_function is the imported original function with the @standard_agent_execution decorator.
    # It will internally instantiate StochasticOscillatorAgent, which our mock_agent_class_factory will intercept.
    result_verdict = await actual_stoch_run_decorated_function(
        symbol=symbol,
        agent_settings=mock_agent_instance.settings, # Pass the settings object
        data_provider=mock_dp_instance,
        mcp_client=mock_mcp_instance,
        k_period=k_p, 
        d_period=d_p, 
        slowing_k=s_k 
    )

    # --- Assertions --- 
    assert result_verdict is not None, "Agent returned None, expected a Verdict object"
    assert isinstance(result_verdict, Verdict), f"Expected Verdict object, got {type(result_verdict)}"
    assert result_verdict.verdict_type == VerdictType[expected_verdict_val], \
        f"Expected verdict {expected_verdict_val}, got {result_verdict.verdict_type.name if result_verdict.verdict_type else None}"
    assert abs(result_verdict.confidence - min_confidence_val) < 0.001, \
        f"Expected confidence {min_confidence_val}, got {result_verdict.confidence}"

    # Assertions for mock calls (cache, data provider, mcp)
    if agent_settings.agent_cache_enabled:
        # The @standard_agent_execution decorator uses the redis client from mock_decorator_redis
        mock_decorator_redis.return_value.get.assert_awaited_once()
        # Since mock_redis_get_side_effect returns None (cache miss), set should be called.
        mock_decorator_redis.return_value.set.assert_awaited_once()
        
        # The agent's own cache_client property (if used by the agent's core logic, 
        # which it might not if the decorator handles all caching) 
        # mock_agent_instance.cache_client.assert_awaited() # This checks if the property itself was awaited
        # mock_base_redis.assert_awaited_once() # This checks if the factory for the agent's client was called
    else:
        mock_decorator_redis.return_value.get.assert_not_awaited()
        mock_decorator_redis.return_value.set.assert_not_awaited()

    # Assert that the agent factory was called by stoch_run to create the agent instance
    # The stoch_run function creates the agent, so the factory should be called.
    mock_agent_class_factory.assert_called_once()
    # You can add more specific assertions about the arguments to the factory if needed, e.g.:
    # mock_agent_class_factory.assert_called_once_with(
    #     settings=mock_agent_instance.settings, 
    #     data_provider=mock_dp_instance, 
    #     mcp_client=mock_mcp_instance
    # )

    # Assert that the core calculation and verdict methods on the (mocked) agent instance were called by stoch_run
    mock_agent_instance._calculate_stochastic_oscillator.assert_awaited_once_with(ANY, ohlcv_data)
    mock_agent_instance._generate_verdict.assert_awaited_once_with(float(min_k), float(min_d), MarketRegime[market_regime_mock])

    # Assert calls to external dependencies
    mock_dp_instance.fetch_ohlcv_series.assert_awaited_once_with(symbol, agent_settings.agent_data_lookback_period)
    mock_mcp_instance.get_context.assert_awaited_once_with(symbol)

    # Clean up any potential side effects from mocks if necessary for other tests (though pytest usually isolates)
    # For example, reset call counts if mocks are shared across parameterized tests in a way that state leaks.
    # However, mocks are generally re-created for each test run in pytest parameterization.

    print(f"Test {test_id} PASSED with verdict: {result_verdict.verdict_type.name if result_verdict.verdict_type else 'None'}, confidence: {result_verdict.confidence}")
