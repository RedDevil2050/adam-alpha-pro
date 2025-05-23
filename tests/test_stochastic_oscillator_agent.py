import sys, os
import datetime
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import pandas as pd
import numpy as np
from unittest.mock import AsyncMock, patch, MagicMock

# Import the agent's run function and the agent class (assuming it exists for patching)
from backend.agents.technical.stochastic_oscillator_agent import run as stoch_run, agent_name

# Define overbought/oversold thresholds used by the agent (adjust if different)
OVERBOUGHT_THRESHOLD = 80 # As per typical use, agent logic implies this
OVERSOLD_THRESHOLD = 20 # As per typical use, agent logic implies this

# Helper to create OHLCV data for specific scenarios
def create_stochastic_data(periods=30, scenario="neutral", k_target=50, d_target=50):
    base_price = 100
    price_range = 20 # Affects K sensitivity

    if scenario == "oversold_buy": # K crosses D upwards in oversold
        # Target: K rises from below D to above D, both < OVERSOLD_THRESHOLD initially
        # e.g., prev_k=10, prev_d=12; latest_k=18, latest_d=15
        low_prices = np.full(periods, base_price - price_range / 2)
        high_prices = np.full(periods, base_price + price_range / 2)
        close_prices = np.full(periods, base_price - price_range / 2 + 0.10 * price_range) # Start with K=10
        close_prices[-4:] = base_price - price_range / 2 + 0.10 * price_range # prev_k for D calc
        close_prices[-3:] = base_price - price_range / 2 + 0.08 * price_range # prev_k for D calc
        close_prices[-2] = base_price - price_range / 2 + 0.05 * price_range  # prev_k = 5
        close_prices[-1] = base_price - price_range / 2 + 0.18 * price_range  # latest_k = 18
    elif scenario == "overbought_sell": # K crosses D downwards in overbought
        # Target: K falls from above D to below D, both > OVERBOUGHT_THRESHOLD initially
        # e.g., prev_k=90, prev_d=88; latest_k=82, latest_d=85
        low_prices = np.full(periods, base_price - price_range / 2)
        high_prices = np.full(periods, base_price + price_range / 2)
        close_prices = np.full(periods, base_price - price_range / 2 + 0.90 * price_range) # Start with K=90
        close_prices[-4:] = base_price - price_range / 2 + 0.90 * price_range
        close_prices[-3:] = base_price - price_range / 2 + 0.92 * price_range
        close_prices[-2] = base_price - price_range / 2 + 0.95 * price_range  # prev_k = 95
        close_prices[-1] = base_price - price_range / 2 + 0.82 * price_range  # latest_k = 82
    else: # Neutral / Hold
        # Sideways movement, K and D around 50
        low_prices = np.linspace(base_price - price_range / 3, base_price - price_range / 2, periods)
        high_prices = np.linspace(base_price + price_range / 3, base_price + price_range / 2, periods)
        close_prices = np.array([low + (high-low) * (0.45 + 0.1 * np.sin(i/3)) for i, (low, high) in enumerate(zip(low_prices, high_prices))]) # Oscillate K around 50

    # Ensure prices are positive
    low_prices = np.maximum(low_prices, 1.0)
    high_prices = np.maximum(high_prices, low_prices + 0.1)
    close_prices = np.clip(close_prices, low_prices, high_prices)
    open_prices = (low_prices + high_prices) / 2 # Simple open

    return pd.DataFrame({
        'high': high_prices,
        'low': low_prices,
        'close': close_prices,
        'open': open_prices,
        'volume': np.random.randint(1000, 5000, periods)
    }, index=pd.date_range(end=datetime.date(2025, 5, 1), periods=periods, freq='D'))

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "test_id, k_p, d_p, s_k, market_regime_mock, data_scenario, expected_verdict_val, min_k, max_k, min_d, max_d, min_confidence_val",
    [
        ("oversold_bull", 14, 3, 3, "BULL", "oversold_buy", "BUY", 5, 25, 5, 25, 0.8),
        ("oversold_neutral", 14, 3, 3, "NEUTRAL", "oversold_buy", "BUY", 5, 25, 5, 25, 0.7),
        ("oversold_bear", 14, 3, 3, "BEAR", "oversold_buy", "BUY", 5, 25, 5, 25, 0.6),
        ("overbought_bull", 14, 3, 3, "BULL", "overbought_sell", "AVOID", 75, 95, 75, 95, 0.6),
        ("overbought_neutral", 14, 3, 3, "NEUTRAL", "overbought_sell", "AVOID", 75, 95, 75, 95, 0.7),
        ("overbought_bear", 20, 5, 5, "BEAR", "overbought_sell", "AVOID", 75, 95, 75, 95, 0.8),
        ("neutral_hold", 14, 3, 3, "NEUTRAL", "neutral", "HOLD", 30, 70, 30, 70, 0.45),
    ]
)
# Patch dependencies in order of execution (innermost to outermost for args)
@patch('backend.agents.technical.stochastic_oscillator_agent.datetime') # mock_datetime_in_agent
@patch('backend.agents.technical.stochastic_oscillator_agent.get_market_context', new_callable=AsyncMock) # mock_agent_get_market_context - Assuming it's a module-level function now
@patch('backend.agents.technical.stochastic_oscillator_agent.fetch_ohlcv_series', new_callable=AsyncMock) # mock_fetch_ohlcv
@patch('backend.agents.base.get_redis_client', new_callable=AsyncMock)  # mock_base_get_redis_client (for AgentBase)
@patch('backend.agents.decorators.get_redis_client', new_callable=AsyncMock) # mock_decorator_redis
@patch('backend.agents.decorators.get_tracker') # mock_decorator_tracker
async def test_stochastic_oscillator_scenarios(
    mock_decorator_tracker,   # Corresponds to decorators.get_tracker
    mock_decorator_redis,    # Corresponds to decorators.get_redis_client
    mock_base_get_redis_client, # Corresponds to base.get_redis_client
    mock_fetch_ohlcv,    # Corresponds to stochastic_oscillator_agent.fetch_ohlcv_series
    mock_agent_get_market_context, # Corresponds to stochastic_oscillator_agent.get_market_context
    mock_datetime_in_agent, # Corresponds to stochastic_oscillator_agent.datetime
    test_id, k_p, d_p, s_k, market_regime_mock, data_scenario, expected_verdict_val, min_k, max_k, min_d, max_d, min_confidence_val
):
    # --- Mock Configuration ---
    symbol = f"TEST_STOCH_{test_id.upper()}"
    num_data_points = max(k_p, d_p, s_k) + 30 # Ensure enough data for calculation

    # Mock datetime
    real_datetime_date_class = datetime.date
    real_datetime_timedelta_class = datetime.timedelta
    mock_today_date_object = real_datetime_date_class(2025, 5, 2)
    mock_datetime_in_agent.date.today.return_value = mock_today_date_object
    mock_datetime_in_agent.datetime.now.return_value = datetime.datetime.combine(mock_today_date_object, datetime.time.min) # if agent uses .now()
    mock_datetime_in_agent.timedelta = real_datetime_timedelta_class

    # Mock data fetching
    price_df = create_stochastic_data(periods=num_data_points, scenario=data_scenario)
    mock_fetch_ohlcv.return_value = price_df

    # Mock market context
    # If get_market_context is now a module-level function called by stoch_run:
    mock_agent_get_market_context.return_value = {"regime": market_regime_mock, "volatility": 0.15}


    # Shared Redis instance
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get = AsyncMock(return_value=None)
    mock_redis_instance.set = AsyncMock()
    mock_decorator_redis.return_value = mock_redis_instance
    mock_base_get_redis_client.return_value = mock_redis_instance

    # Mock Tracker instance
    mock_tracker_instance = MagicMock()
    mock_tracker_instance.update_agent_status = AsyncMock()
    mock_decorator_tracker.return_value = mock_tracker_instance

    # --- Run Agent ---
    result = await stoch_run(symbol, k_period=k_p, d_period=d_p, smooth_k=s_k)

    # --- Assertions ---
    assert result is not None
    assert result.get('error') is None, f"Agent returned error: {result.get('error')}"
    assert result['symbol'] == symbol
    assert result['agent_name'] == agent_name
    assert result['verdict'] == expected_verdict_val
    assert 'details' in result
    details = result['details']
    assert 'k' in details and 'd' in details
    assert min_k <= details['k'] <= max_k, f"K value {details['k']} out of expected range [{min_k}, {max_k}] for {test_id}"
    assert min_d <= details['d'] <= max_d, f"D value {details['d']} out of expected range [{min_d}, {max_d}] for {test_id}"

    if expected_verdict_val == "BUY":
        assert details['k'] > details['d'], "For BUY, K should be > D"
    elif expected_verdict_val == "AVOID":
        assert details['k'] < details['d'], "For AVOID, K should be < D"

    assert result['confidence'] >= min_confidence_val
    assert result['confidence'] <= 1.0
    assert details['market_regime'] == market_regime_mock
    assert details['params'] == {'k': k_p, 'd': d_p, 's': s_k}

    # --- Verify Mocks ---
    # Agent's internal logic for start_date calculation might depend on k_p, d_p, s_k.
    # Assuming a fixed lookback for now, or this would need to be dynamic.
    expected_end_date_for_fetch = mock_today_date_object
    expected_start_date_for_fetch = expected_end_date_for_fetch - real_datetime_timedelta_class(days=max(k_p,d_p,s_k) + 60) # Adjusted lookback based on params

    mock_fetch_ohlcv.assert_awaited_once_with(symbol, start_date=expected_start_date_for_fetch, end_date=expected_end_date_for_fetch)
    # Verify get_market_context mock if it's used by stoch_run
    if mock_agent_get_market_context.called: # Check if it was called
        mock_agent_get_market_context.assert_awaited_once_with(symbol)

    mock_decorator_redis.assert_awaited_once()
    mock_base_get_redis_client.assert_awaited_once()
    assert mock_redis_instance.get.await_count == 2 # Decorator + AgentBase
    if result.get('verdict') not in ['NO_DATA', 'ERROR', None]:
        assert mock_redis_instance.set.await_count == 2 # Decorator + AgentBase
    else:
        mock_redis_instance.set.assert_not_awaited()

    mock_decorator_tracker.assert_called_once()
    mock_tracker_instance.update_agent_status.assert_awaited_once()
