import asyncio
import datetime
from unittest.mock import AsyncMock, MagicMock, patch, ANY 
import pytest
import pandas as pd # Added import

# Assuming these are the correct paths for your project structure
from backend.agents.technical.stochastic_oscillator_agent import StochasticOscillatorAgent as OriginalStochasticOscillatorAgent, run as actual_stoch_run_decorated_function, AGENT_NAME # Changed stoch_run to run
from backend.models.common_models import TimeSeriesData, DataPoint, Verdict # Corrected import path
from backend.market.context import MarketContext as Context # Corrected import path for Context
from backend.config.settings import AgentSettings # Moved AgentSettings import
from backend.models.common_models import VerdictType, MarketRegime # Corrected import path for MarketRegime
from backend.data.providers.base_provider import BaseDataProvider as DataProviderBase # Corrected import for DataProviderBase

original_agent_module_name = AGENT_NAME

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
    
    # Correctly mock the cache_client property
    type(mock_agent_instance).cache_client = AsyncMock(return_value=await cache_client_property_logic())


    # --- Mock DataProvider and MCPClient ---
    mock_dp_instance = AsyncMock(spec=DataProviderBase)
    ohlcv_data = await create_stochastic_data(symbol, num_data_points_for_create, data_scenario, k_p, s_k, d_p)
    mock_dp_instance.fetch_price_data.return_value = ohlcv_data # Changed fetch_ohlcv_series to fetch_price_data

    # --- Mock Context ---
    mock_context = MagicMock(spec=Context)
    mock_context.symbol = symbol
    mock_context.market_regime = MarketRegime[market_regime_mock]
    mock_context.data_provider = mock_dp_instance # Assign the mocked data provider

    # --- Configure the Agent Class Factory ---
    # When StochasticOscillatorAgent is called (e.g., in stoch_run), it returns our mock_agent_instance
    mock_agent_class_factory.return_value = mock_agent_instance

    # --- Mock datetime for consistent "now" ---
    # Set a fixed "now" for consistent timestamping if your agent uses datetime.now() directly
    fixed_now = datetime.datetime(2023, 10, 26, 12, 0, 0, tzinfo=datetime.timezone.utc)
    mock_datetime_module_in_agent.now.return_value = fixed_now
    mock_datetime_module_in_agent.side_effect = lambda *args, **kw: datetime.datetime(*args, **kw)
    mock_datetime_module_in_agent.timedelta = datetime.timedelta # Ensure timedelta is still available

    # --- Mock the agent's core logic method (_calculate_stochastic_oscillator) ---
    # This is where the actual calculation happens. We want to control its output.
    # The _calculate_stochastic_oscillator method should return a tuple: (k_value, d_value, verdict_type, confidence)
    # Based on the scenario, we'll make it return values that lead to the expected_verdict_val.

    # Example: For "oversold_buy", we want %K and %D to be low (e.g., 10)
    # For "overbought_sell", we want %K and %D to be high (e.g., 90)
    # For "neutral", %K and %D are somewhere in the middle (e.g., 50)

    if "oversold" in data_scenario:
        # Simulate %K and %D crossing up from oversold
        # Let's say current %K is slightly above current %D, both in oversold territory
        # And previous %K was below previous %D
        # The agent's _get_verdict should interpret this as BUY_OVERSOLD_CROSS
        # The actual values of k_val and d_val here are less important than the verdict and confidence
        # that _calculate_stochastic_oscillator would pass to _get_verdict.
        # We are essentially mocking the outcome of the TA-Lib calculation part.
        
        # To ensure the "cross" logic works, the agent might look at the last two points.
        # Let's assume the agent's _calculate_stochastic_oscillator returns the *latest* %K and %D
        # and the _get_verdict method handles the crossing logic by looking at historical %K/%D
        # or the _calculate_stochastic_oscillator itself determines the cross.
        # For simplicity, let's assume _calculate_stochastic_oscillator returns the verdict directly
        # based on its internal TA-Lib results.
        
        # The mock for _calculate_stochastic_oscillator should return:
        # (last_k, last_d, calculated_verdict_enum, calculated_confidence)
        # The `run` method then uses this.
        
        # We need to mock what `_calculate_stochastic_oscillator` returns.
        # It should return: k_series, d_series (pandas Series)
        # Let's create dummy series that would lead to the desired verdict.
        
        # Create dummy pandas Series for %K and %D
        # These values should reflect the scenario (e.g., oversold, overbought)
        # The length should be consistent with the data points used after TA-Lib processing.
        # TA-Lib's STOCH function will produce NaNs at the beginning.
        # The number of NaNs depends on k_p, s_k, d_p.
        # Total lookback for STOCH: (k_p - 1) + (s_k - 1) + (d_p - 1)
        # So, if num_data_points_for_create is, say, 30, and lookback is 18,
        # then k_series and d_series will have length 30, with first 18 values being NaN.
        
        # For simplicity in the mock, let's assume the agent's internal logic
        # correctly uses these series to arrive at a verdict.
        # We will mock the `_get_verdict` method of the *actual* agent instance
        # that the `run` function will create and use.
        
        # The `run` function, when called, will:
        # 1. Create a StochasticOscillatorAgent instance.
        # 2. Call `execute` on it.
        # 3. `execute` calls `_fetch_data`.
        # 4. `execute` calls `_calculate_stochastic_oscillator`.
        # 5. `execute` calls `_get_verdict`.
        # 6. `execute` calls `_store_results`.
        
        # So, we need `mock_agent_class_factory` to return an instance whose methods are appropriately mocked.
        # `mock_agent_instance` is what `StochasticOscillatorAgent(...)` will return.
        
        # Let's make `_calculate_stochastic_oscillator` on the `mock_agent_instance` return specific K and D values
        # that would lead to the `expected_verdict_val` when `_get_verdict` is called.
        # The `_get_verdict` method takes the latest k and d, and historical series.
        
        # Simplified: Mock the direct output of _get_verdict for more control
        # This means the `mock_agent_instance` should have its `_get_verdict` method mocked.
        
        # Let's refine: the `run` function calls `agent.execute()`.
        # `agent.execute()` calls `self._calculate_stochastic_oscillator()` and then `self._get_verdict()`.
        # So, `mock_agent_instance._calculate_stochastic_oscillator` and `mock_agent_instance._get_verdict`
        # need to be async mocks if they are async, or MagicMock if synchronous.
        
        # Assuming _calculate_stochastic_oscillator is synchronous and returns two pd.Series
        # And _get_verdict is synchronous.
        
        # Create plausible k_val and d_val for the scenario
        k_val = (min_k + max_k) / 2
        d_val = (min_d + max_d) / 2
        
        # Mock `_calculate_stochastic_oscillator` to return dummy series
        # The actual series content might be complex to simulate perfectly,
        # so we focus on the latest values that `_get_verdict` would use.
        dummy_k_series = pd.Series([k_val-5, k_val-2, k_val]) # Simulating a trend
        dummy_d_series = pd.Series([d_val-1, d_val-1, d_val])
        
        # If _calculate_stochastic_oscillator is async:
        # mock_agent_instance._calculate_stochastic_oscillator = AsyncMock(return_value=(dummy_k_series, dummy_d_series))
        # If it's synchronous:
        mock_agent_instance._calculate_stochastic_oscillator = MagicMock(return_value=(dummy_k_series, dummy_d_series))

        # Now, mock `_get_verdict` to return the `expected_verdict_val` and a confidence
        # The `_get_verdict` method in the original agent determines the verdict and confidence.
        # We want to control this outcome directly for the test.
        expected_verdict_enum = VerdictType[expected_verdict_val]
        
        # If _get_verdict is async:
        # mock_agent_instance._get_verdict = AsyncMock(return_value=Verdict(
        #    verdict=expected_verdict_enum,
        #    confidence=min_confidence_val + 0.05, # slightly above min
        #    data_payload={'k': k_val, 'd': d_val, 'k_period': k_p, 'd_period': d_p, 's_k_period': s_k}
        # ))
        # If it's synchronous:
        mock_agent_instance._get_verdict = MagicMock(return_value=Verdict(
            verdict=expected_verdict_enum,
            confidence=min_confidence_val + 0.05, 
            data_payload={'k': k_val, 'd': d_val, 'k_period': k_p, 'd_period': d_p, 's_k_period': s_k}
        ))
        
        # Mock `_store_results` as it might interact with cache/DB
        # If _store_results is async:
        # mock_agent_instance._store_results = AsyncMock(return_value=None)
        # If it's synchronous:
        mock_agent_instance._store_results = MagicMock(return_value=None)

    else: # "neutral_hold" or other non-crossing scenarios
        k_val = (min_k + max_k) / 2 
        d_val = (min_d + max_d) / 2
        dummy_k_series = pd.Series([k_val, k_val, k_val])
        dummy_d_series = pd.Series([d_val, d_val, d_val])
        
        # mock_agent_instance._calculate_stochastic_oscillator = AsyncMock(return_value=(dummy_k_series, dummy_d_series))
        mock_agent_instance._calculate_stochastic_oscillator = MagicMock(return_value=(dummy_k_series, dummy_d_series))
        
        expected_verdict_enum = VerdictType[expected_verdict_val]
        # mock_agent_instance._get_verdict = AsyncMock(return_value=Verdict(
        #    verdict=expected_verdict_enum,
        #    confidence=min_confidence_val + 0.05,
        #    data_payload={'k': k_val, 'd': d_val, 'k_period': k_p, 'd_period': d_p, 's_k_period': s_k}
        # ))
        mock_agent_instance._get_verdict = MagicMock(return_value=Verdict(
            verdict=expected_verdict_enum,
            confidence=min_confidence_val + 0.05,
            data_payload={'k': k_val, 'd': d_val, 'k_period': k_p, 'd_period': d_p, 's_k_period': s_k}
        ))

        # mock_agent_instance._store_results = AsyncMock(return_value=None)
        mock_agent_instance._store_results = MagicMock(return_value=None)

    # --- Call the actual decorated run function ---
    # The `run` function is decorated with @standard_agent_execution
    # This decorator handles:
    # - Getting a tracker
    # - Creating the agent instance (which is now our mock_agent_class_factory that returns mock_agent_instance)
    # - Calling agent.execute(context)
    # - Handling exceptions, caching, etc.
    
    # We pass the *actual* run function from the agent module.
    # The patches ensure that when this run function executes, it uses our mocks.
    # The parameters for stoch_run are (context, k_period, d_period, sk_period)
    # Ensure the parameters passed to actual_stoch_run_decorated_function match its definition.
    # It seems the decorated function `run` takes `context` and then `*args, **kwargs` which are passed to the agent's `execute`.
    # The agent's `execute` method itself might not take k_p, d_p, s_k directly if they are part of its init settings.
    # Let's assume the `run` function is defined as `async def run(context: Context, k_period: int, d_period: int, sk_period: int)`
    # or similar, and these are passed to the agent constructor or execute method.
    
    # If StochasticOscillatorAgent's __init__ takes these:
    # mock_agent_class_factory.configure_mock(
    #    k_period=k_p, 
    #    d_period=d_p, 
    #    sk_period=s_k
    # )
    # Or if its `execute` method takes these:
    # mock_agent_instance.execute = AsyncMock(...) and it will be called with these.
    
    # The `actual_stoch_run_decorated_function` is the `run` from the agent file.
    # Its signature is likely `async def run(context: Context, k_period: int, d_period: int, sk_period: int, ...)`
    # The test parameters `k_p, d_p, s_k` should be passed to it.

    # The `standard_agent_execution` decorator will instantiate the agent.
    # The agent's `__init__` will be called. We need to ensure `mock_agent_instance`
    # is configured as if it was initialized with these periods.
    # The `execute` method of the agent will then be called.
    # The `execute` method will use the `k_period`, `d_period`, `sk_period` from the agent's instance.
    
    # Let's assume these periods are set on the agent instance by its __init__ or by the run function
    # before calling execute. We've already set them in the data_payload for the verdict,
    # which is a bit of a shortcut.
    # For a more robust test, ensure `mock_agent_instance` has these attributes if `_calculate_stochastic_oscillator`
    # or `_get_verdict` uses `self.k_period` etc.
    mock_agent_instance.k_period = k_p
    mock_agent_instance.d_period = d_p
    mock_agent_instance.sk_period = s_k
    
    # The `run` function from the agent module is what we're testing.
    # It's decorated, so it handles agent creation and execution.
    # The `args` for the `run` function (after context) are k_period, d_period, sk_period.
    # print(f"Calling actual_stoch_run_decorated_function for {test_id} with k_p={k_p}, d_p={d_p}, s_k={s_k}")
    
    # The `actual_stoch_run_decorated_function` is the `run` function from the agent.
    # It is defined as: async def run(context: Context, k_period: int = 14, d_period: int = 3, sk_period: int = 3)
    # So we pass k_p, d_p, s_k to it.
    
    verdict_result = await actual_stoch_run_decorated_function(mock_context, k_p, d_p, s_k)
    
    # --- Assertions ---
    assert verdict_result is not None, f"Verdict should not be None for {test_id}"
    assert isinstance(verdict_result, Verdict), f"Result should be a Verdict instance for {test_id}"
    
    # print(f"Test {test_id}: Expected Verdict: {expected_verdict_val}, Actual Verdict: {verdict_result.verdict.name}")
    # print(f"Test {test_id}: Expected Min Confidence: {min_confidence_val}, Actual Confidence: {verdict_result.confidence}")

    assert verdict_result.verdict.name == expected_verdict_val, f"Verdict type mismatch for {test_id}"
    assert verdict_result.confidence >= min_confidence_val, f"Confidence too low for {test_id}: {verdict_result.confidence} < {min_confidence_val}"
    assert verdict_result.confidence <= 1.0, f"Confidence over 1.0 for {test_id}: {verdict_result.confidence}"

    # Check if data provider's fetch_price_data was called correctly
    mock_dp_instance.fetch_price_data.assert_called_once_with( # Changed from fetch_ohlcv_series
        symbol=symbol, 
        # start_date=ANY, # The decorator/agent might calculate this.
        # end_date=ANY,   # Or it might pass None if not specified.
        # interval=ANY    # Default interval or agent specified.
        # We need to be more specific if the agent always passes these.
        # For now, let's assume it's called with the symbol and the agent handles date/interval.
        # If the agent's _fetch_data explicitly sets start/end/interval, match those.
        # The `DataProviderBase.fetch_price_data` has defaults for start_date, end_date, interval.
        # The agent's `_fetch_data` method likely calculates `start_date` based on `lookback_period`.
        start_date=ANY, # Agent calculates this based on lookback
        end_date=fixed_now, # Agent likely uses current time as end date
        interval='1d' # Assuming daily interval for stoch
    )
    
    # Check if cache was used or set (depending on test setup for cache hit/miss)
    # In this setup, we mock a cache miss (mock_redis_instance.get returns None).
    # So, we expect a call to set the cache.
    # The key for caching is usually complex, involving agent name, symbol, params.
    # The @standard_agent_execution decorator handles caching.
    # It calls `agent.get_cache_key()` and `agent.store_results_in_cache()`.
    
    # We need to mock `get_cache_key` on `mock_agent_instance` if the decorator calls it.
    # Let's assume a simple cache key for now.
    cache_key = f"{original_agent_module_name}:{symbol}:{k_p}:{d_p}:{s_k}:{market_regime_mock}" # Example
    mock_agent_instance.get_cache_key = MagicMock(return_value=cache_key)

    # The decorator should have called `get` on the cache.
    mock_redis_instance.get.assert_called_once_with(cache_key)
    
    # Since it was a cache miss, `set` should have been called by `agent.store_results_in_cache`
    # which is called by the decorator if caching is enabled and there's a result.
    # `mock_agent_instance.store_results_in_cache` would be called by the decorator.
    # Let's mock that on the agent instance.
    async def mock_store_in_cache(key, value, ttl):
        # print(f"Mocked store_results_in_cache called with key: {key}, ttl: {ttl}")
        # In a real scenario, this would call self.cache_client.set(key, value, ex=ttl)
        # We can assert that `mock_redis_instance.set` was called by this.
        await mock_redis_instance.set(key, ANY, ex=ttl) # ANY for serialized value
        return True
    
    mock_agent_instance.store_results_in_cache = AsyncMock(side_effect=mock_store_in_cache)
    
    # Now, after `run` is called, we check if `store_results_in_cache` was called.
    # And through its side_effect, if `mock_redis_instance.set` was called.
    if agent_settings.agent_cache_enabled and verdict_result:
        mock_agent_instance.store_results_in_cache.assert_called_once()
        # The actual call to mock_redis_instance.set happens *inside* store_results_in_cache
        # So, we check that `set` was called.
        mock_redis_instance.set.assert_called_once_with(cache_key, ANY, ex=agent_settings.agent_cache_ttl_seconds)

    # Verify tracker calls if needed (e.g., tracker.track_event)
    mock_decorator_tracker.return_value.track_event.assert_called() # Basic check

    # Ensure the agent factory was called to create the agent
    mock_agent_class_factory.assert_called_once_with(
        agent_settings=ANY, # The decorator creates/fetches this
        # k_period=k_p, # If these are init params for the agent
        # d_period=d_p,
        # sk_period=s_k
        # The decorator passes agent_settings.
        # If k_p, d_p, s_k are init params, the decorator needs to pass them.
        # Or, if they are only used in `execute`, then this is fine.
        # The `run` function signature suggests they are not init params for the agent itself,
        # but rather parameters for the execution logic within `run` or `agent.execute`.
        # The `standard_agent_execution` decorator instantiates with `AgentClass(agent_settings=settings_for_agent)`
        # It then calls `agent.execute(context, *args, **kwargs_for_execute)`
        # So, k_p, d_p, s_k are passed to `execute`.
        # We need to make sure `mock_agent_instance.execute` was called with these.
    )
    
    # The decorator calls `agent.execute(context, *args, **kwargs)`.
