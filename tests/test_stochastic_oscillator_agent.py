import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import pandas as pd
import numpy as np
from unittest.mock import AsyncMock, patch, MagicMock
# Import the agent's run function
from backend.agents.technical.stochastic_oscillator_agent import run as stoch_run

# Optional: If you have a standard TA library, you could import it to verify
# the data generation produces the expected K and D values.
# from ta.momentum import StochasticOscillator

agent_name = "stochastic_oscillator_agent" # Match agent's name

# Define overbought/oversold thresholds used by the agent (adjust if different)
OVERBOUGHT_THRESHOLD = 80
OVERSOLD_THRESHOLD = 20

@pytest.mark.asyncio
# Patch dependencies
@patch('backend.agents.decorators.get_tracker')
# Correct patch target: where get_redis_client is IMPORTED/USED in the agent module
@patch('backend.agents.technical.stochastic_oscillator_agent.get_redis_client')
@patch('backend.agents.technical.stochastic_oscillator_agent.fetch_ohlcv_series') # Correct patch target
async def test_stochastic_oscillator_overbought_crossover(
    mock_fetch_ohlcv,
    mock_get_redis,
    mock_get_tracker,
):
    """
    Test Stochastic Oscillator agent for K crossing below D in the overbought zone.
    This scenario should typically result in a 'SELL' or 'AVOID' signal
    according to standard interpretation.
    """
    # --- Mock Configuration ---
    symbol = "TEST_STOCH_OB_CROSS"
    k_window = 14 # Assuming default window
    d_window = 3 # Assuming default window

    # Generate price data specifically designed to force K and D into
    # overbought territory and then cause K to drop below D.
    # A long upward trend, then a slight dip at the end.
    num_periods_warmup = 100 # Enough periods to get moving averages stable
    num_periods_test = k_window + d_window + 5 # Periods needed for calculations plus a few
    total_periods = num_periods_warmup + num_periods_test

    # Create a strong upward trend
    prices_warmup = np.linspace(50, 150, num_periods_warmup)
    # Continue at a high value, then simulate a slight drop at the very end
    prices_test = np.full(num_periods_test, 150.0) # Plateau at high value
    # Force the last couple of closes to drop slightly, causing K to drop
    prices_test[-2] = 149.0 # Slight dip
    prices_test[-1] = 147.0 # Further dip

    prices = np.concatenate((prices_warmup, prices_test))

    # Generate OHLC data based on prices, ensuring high/low are around close
    highs = prices + np.random.uniform(0.1, 0.5, total_periods)
    lows = prices - np.random.uniform(0.1, 0.5, total_periods)
    closes = prices.copy()
    opens = closes - np.random.uniform(-0.1, 0.1, total_periods)

    # Ensure high >= close >= low
    highs = np.maximum(highs, closes)
    lows = np.minimum(lows, closes)

    ohlcv_df = pd.DataFrame({
        'high': highs,
        'low': lows,
        'close': closes,
        'open': opens,
        'volume': np.random.randint(1000, 5000, total_periods)
    }, index=pd.date_range(end='2025-05-01', periods=total_periods, freq='D'))

    # --- Self-Verification of Generated Data ---
    # Calculate K and D within the test to confirm the data simulates the scenario
    low_min_calc = ohlcv_df["low"].rolling(k_window).min()
    high_max_calc = ohlcv_df["high"].rolling(k_window).max()
    # Avoid division by zero if high == low for a period
    range_hl = high_max_calc - low_min_calc
    k_calc = 100 * ((ohlcv_df["close"] - low_min_calc) / range_hl.replace(0, np.nan)) # Replace 0 range with NaN
    k_calc = k_calc.fillna(method='ffill').fillna(method='bfill') # Handle NaNs if any

    d_calc = k_calc.rolling(d_window).mean()

    # Get the last calculated K and D values
    last_k = k_calc.iloc[-1]
    last_d = d_calc.iloc[-1]
    prev_k = k_calc.iloc[-2] # Need previous values to check for crossover
    prev_d = d_calc.iloc[-2]

    print(f"\n--- Data Verification for {symbol} ---")
    print(f"Last K: {last_k:.2f}, Last D: {last_d:.2f}")
    print(f"Previous K: {prev_k:.2f}, Previous D: {prev_d:.2f}")
    print(f"K < D: {last_k < last_d}")
    print(f"Previous K >= Previous D: {prev_k >= prev_d}") # Check for crossover direction
    print(f"Is Overbought (> {OVERBOUGHT_THRESHOLD})? K: {last_k > OVERBOUGHT_THRESHOLD}, D: {last_d > OVERBOUGHT_THRESHOLD}")
    print("------------------------------------")

    # Assert that the generated data fulfills the conditions for the test scenario
    assert last_k < last_d, "Generated data did not result in last_k < last_d"
    assert prev_k >= prev_d, "Generated data did not result in prev_k >= prev_d for crossover check"
    # Assert that the crossover happened in the overbought zone
    # We need *either* K or D (or both) to be in the overbought zone around the crossover
    # A common check is if D is overbought, or if K was overbought before dropping.
    # Let's check if D was in overbought before the drop.
    assert prev_d > OVERBOUGHT_THRESHOLD, f"Previous D ({prev_d:.2f}) was not in overbought zone (> {OVERBOUGHT_THRESHOLD})"
    # assert prev_k > OVERBOUGHT_THRESHOLD, f"Previous K ({prev_k:.2f}) was not in overbought zone (> {OVERBOUGHT_THRESHOLD})" # Alternative/additional check

    # --- End Data Verification ---


    # 1. Mock fetch_ohlcv_series
    mock_fetch_ohlcv.return_value = ohlcv_df

    # 2. Mock Redis
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get.return_value = None # Cache miss
    mock_redis_instance.set = AsyncMock()
    # Configure the mock factory to return the instance when awaited
    mock_get_redis.return_value = mock_redis_instance

    # 3. Mock Tracker via decorator patch
    mock_tracker_instance = AsyncMock()
    mock_tracker_instance.update_agent_status = AsyncMock()
    mock_get_tracker.return_value = mock_tracker_instance

    # --- Expected Results ---
    # Based on standard interpretation of K crossing below D in overbought
    expected_verdict = "AVOID" # Or "SELL", depends on your agent's enum

    # --- Run Agent ---
    result = await stoch_run(symbol)

    # --- Assertions ---
    assert result is not None, "Agent should return a result dictionary"
    assert 'symbol' in result and result['symbol'] == symbol
    assert 'agent_name' in result and result['agent_name'] == agent_name
    assert 'verdict' in result
    assert 'value' in result
    assert 'details' in result
    assert 'k' in result['details']
    assert 'd' in result['details']

    # Check for error first
    assert result.get('error') is None, f"Agent returned error: {result.get('error')}"

    # Assert the calculated K and D values in the result match the data's final values
    # Allow a small floating point tolerance
    assert pytest.approx(result['details']['k'], abs=0.1) == last_k, f"Agent's K ({result['details']['k']:.2f}) does not match calculated K ({last_k:.2f})"
    assert pytest.approx(result['details']['d'], abs=0.1) == last_d, f"Agent's D ({result['details']['d']:.2f}) does not match calculated D ({last_d:.2f})"

    # Assert the expected verdict
    assert result['verdict'] == expected_verdict, \
        f"Expected verdict '{expected_verdict}' for OB crossover, got '{result['verdict']}'. Details: {result.get('details')}"

    # Optional: Also assert that the K and D values reported in the result
    # are consistent with the overbought range and the crossover
    assert result['details']['k'] < result['details']['d'], "Result details should show K < D"
    # This check depends on how the agent reports - does it report the exact last value
    # or the state *after* the calculation? Let's check the state *around* the crossover.
    # We already verified the input data creates this state; the agent should report it.
    # Check if the verdict is indeed triggered by the overbought condition
    # This might be implicitly tested by the verdict assertion, but can be explicit
    # assert result['details']['d'] > OVERBOUGHT_THRESHOLD # Example check if D determines OB state

    # --- Verify Mocks ---
    mock_fetch_ohlcv.assert_awaited_once_with(symbol)
    mock_get_redis.assert_awaited_once() # Verify the factory function was called once and awaited
    mock_redis_instance.get.assert_awaited_once_with(f"{agent_name}:{symbol}")
    # Assuming the agent caches non-error/non-NO_DATA results
    if result.get('verdict') not in ['ERROR', 'NO_DATA']:
        # The exact value passed to set depends on agent's caching format
        mock_redis_instance.set.assert_awaited_once()
    else:
        # If the agent doesn't cache ERROR/NO_DATA, assert not awaited
        mock_redis_instance.set.assert_not_awaited() # Changed based on likely caching logic

    # Verify tracker was called via the decorator
    mock_get_tracker.assert_called_once() # Correct assertion for the patched factory function
    mock_tracker_instance.update_agent_status.assert_awaited_once()


# Add tests for other scenarios (oversold crossover, neutral, etc.)
@pytest.mark.asyncio
@patch('backend.agents.decorators.get_tracker')
@patch('backend.agents.technical.stochastic_oscillator_agent.get_redis_client')
@patch('backend.agents.technical.stochastic_oscillator_agent.fetch_ohlcv_series')
async def test_stochastic_oscillator_oversold_crossover(
    mock_fetch_ohlcv,
    mock_get_redis,
    mock_get_tracker,
):
    """
    Test Stochastic Oscillator agent for K crossing above D in the oversold zone.
    This scenario should typically result in a 'BUY' signal.
    """
    symbol = "TEST_STOCH_OS_CROSS"
    k_window = 14
    d_window = 3

    num_periods_warmup = 100
    num_periods_test = k_window + d_window + 5
    total_periods = num_periods_warmup + num_periods_test

    # Create a strong downward trend
    prices_warmup = np.linspace(150, 50, num_periods_warmup)
    # Continue at a low value, then simulate a slight rise at the very end
    prices_test = np.full(num_periods_test, 50.0) # Plateau at low value
    # Force the last couple of closes to rise slightly, causing K to rise
    prices_test[-2] = 51.0 # Slight rise
    prices_test[-1] = 53.0 # Further rise

    prices = np.concatenate((prices_warmup, prices_test))

    highs = prices + np.random.uniform(0.1, 0.5, total_periods)
    lows = prices - np.random.uniform(0.1, 0.5, total_periods)
    closes = prices.copy()
    opens = closes - np.random.uniform(-0.1, 0.1, total_periods)

    highs = np.maximum(highs, closes)
    lows = np.minimum(lows, closes)

    ohlcv_df = pd.DataFrame({
        'high': highs,
        'low': lows,
        'close': closes,
        'open': opens,
        'volume': np.random.randint(1000, 5000, total_periods)
    }, index=pd.date_range(end='2025-05-01', periods=total_periods, freq='D'))

    # --- Self-Verification of Generated Data ---
    low_min_calc = ohlcv_df["low"].rolling(k_window).min()
    high_max_calc = ohlcv_df["high"].rolling(k_window).max()
    range_hl = high_max_calc - low_min_calc
    k_calc = 100 * ((ohlcv_df["close"] - low_min_calc) / range_hl.replace(0, np.nan))
    k_calc = k_calc.fillna(method='ffill').fillna(method='bfill')

    d_calc = k_calc.rolling(d_window).mean()

    last_k = k_calc.iloc[-1]
    last_d = d_calc.iloc[-1]
    prev_k = k_calc.iloc[-2]
    prev_d = d_calc.iloc[-2]

    print(f"\n--- Data Verification for {symbol} ---")
    print(f"Last K: {last_k:.2f}, Last D: {last_d:.2f}")
    print(f"Previous K: {prev_k:.2f}, Previous D: {prev_d:.2f}")
    print(f"K > D: {last_k > last_d}")
    print(f"Previous K <= Previous D: {prev_k <= prev_d}") # Check for crossover direction
    print(f"Is Oversold (< {OVERSOLD_THRESHOLD})? K: {last_k < OVERSOLD_THRESHOLD}, D: {last_d < OVERSOLD_THRESHOLD}")
    print("------------------------------------")

    assert last_k > last_d, "Generated data did not result in last_k > last_d"
    assert prev_k <= prev_d, "Generated data did not result in prev_k <= prev_d for crossover check"
    assert prev_d < OVERSOLD_THRESHOLD, f"Previous D ({prev_d:.2f}) was not in oversold zone (< {OVERSOLD_THRESHOLD})"

    # --- End Data Verification ---

    mock_fetch_ohlcv.return_value = ohlcv_df

    mock_redis_instance = AsyncMock()
    mock_redis_instance.get.return_value = None
    mock_redis_instance.set = AsyncMock()
    mock_get_redis.return_value = mock_redis_instance

    mock_tracker_instance = AsyncMock()
    mock_tracker_instance.update_agent_status = AsyncMock()
    mock_get_tracker.return_value = mock_tracker_instance

    expected_verdict = "BUY" # Or whatever your agent returns for oversold crossover

    result = await stoch_run(symbol)

    assert result is not None
    assert 'symbol' in result and result['symbol'] == symbol
    assert 'agent_name' in result and result['agent_name'] == agent_name
    assert 'verdict' in result
    assert 'value' in result
    assert 'details' in result
    assert 'k' in result['details']
    assert 'd' in result['details']

    assert result.get('error') is None, f"Agent returned error: {result.get('error')}"

    assert pytest.approx(result['details']['k'], abs=0.1) == last_k
    assert pytest.approx(result['details']['d'], abs=0.1) == last_d

    assert result['verdict'] == expected_verdict, \
        f"Expected verdict '{expected_verdict}' for OS crossover, got '{result['verdict']}'. Details: {result.get('details')}"

    assert result['details']['k'] > result['details']['d'], "Result details should show K > D"

    mock_fetch_ohlcv.assert_awaited_once_with(symbol)
    mock_get_redis.assert_awaited_once()
    mock_redis_instance.get.assert_awaited_once_with(f"{agent_name}:{symbol}")
    if result.get('verdict') not in ['ERROR', 'NO_DATA']:
        mock_redis_instance.set.assert_awaited_once()
    else:
        mock_redis_instance.set.assert_not_awaited()

    mock_get_tracker.assert_called_once()
    mock_tracker_instance.update_agent_status.assert_awaited_once()

# Optional: Add a test for a neutral scenario (K/D between 20-80)
@pytest.mark.asyncio
@patch('backend.agents.decorators.get_tracker')
@patch('backend.agents.technical.stochastic_oscillator_agent.get_redis_client')
@patch('backend.agents.technical.stochastic_oscillator_agent.fetch_ohlcv_series')
async def test_stochastic_oscillator_neutral(
    mock_fetch_ohlcv,
    mock_get_redis,
    mock_get_tracker,
):
    """
    Test Stochastic Oscillator agent for K and D in the neutral zone (20-80).
    Should typically result in a 'HOLD' signal.
    """
    symbol = "TEST_STOCH_NEUTRAL"
    k_window = 14
    d_window = 3

    num_periods = k_window + d_window + 50 # Enough periods for stable calculation

    # Create data with price fluctuations that keep K and D in the middle range
    # A sideway or slightly trending market
    prices = np.linspace(100, 110, num_periods) + np.sin(np.linspace(0, 4 * np.pi, num_periods)) * 5 # Sideways movement with waves

    highs = prices + np.random.uniform(0.1, 0.5, num_periods)
    lows = prices - np.random.uniform(0.1, 0.5, num_periods)
    closes = prices.copy()
    opens = closes - np.random.uniform(-0.1, 0.1, num_periods)

    highs = np.maximum(highs, closes)
    lows = np.minimum(lows, closes)

    ohlcv_df = pd.DataFrame({
        'high': highs,
        'low': lows,
        'close': closes,
        'open': opens,
        'volume': np.random.randint(1000, 5000, num_periods)
    }, index=pd.date_range(end='2025-05-01', periods=num_periods, freq='D'))

    # --- Self-Verification of Generated Data ---
    low_min_calc = ohlcv_df["low"].rolling(k_window).min()
    high_max_calc = ohlcv_df["high"].rolling(k_window).max()
    range_hl = high_max_calc - low_min_calc
    k_calc = 100 * ((ohlcv_df["close"] - low_min_calc) / range_hl.replace(0, np.nan))
    k_calc = k_calc.fillna(method='ffill').fillna(method='bfill')

    d_calc = k_calc.rolling(d_window).mean()

    last_k = k_calc.iloc[-1]
    last_d = d_calc.iloc[-1]

    print(f"\n--- Data Verification for {symbol} ---")
    print(f"Last K: {last_k:.2f}, Last D: {last_d:.2f}")
    print(f"Is Neutral ({OVERSOLD_THRESHOLD}-{OVERBOUGHT_THRESHOLD})? K: {OVERSOLD_THRESHOLD <= last_k <= OVERBOUGHT_THRESHOLD}, D: {OVERSOLD_THRESHOLD <= last_d <= OVERBOUGHT_THRESHOLD}")
    print("------------------------------------")

    # Assert that the generated data results in K and D within the neutral zone
    assert OVERSOLD_THRESHOLD <= last_k <= OVERBOUGHT_THRESHOLD, f"Last K ({last_k:.2f}) not in neutral zone"
    assert OVERSOLD_THRESHOLD <= last_d <= OVERBOUGHT_THRESHOLD, f"Last D ({last_d:.2f}) not in neutral zone"

    # --- End Data Verification ---

    mock_fetch_ohlcv.return_value = ohlcv_df

    mock_redis_instance = AsyncMock()
    mock_redis_instance.get.return_value = None
    mock_redis_instance.set = AsyncMock()
    mock_get_redis.return_value = mock_redis_instance

    mock_tracker_instance = AsyncMock()
    mock_tracker_instance.update_agent_status = AsyncMock()
    mock_get_tracker.return_value = mock_tracker_instance

    expected_verdict = "HOLD"

    result = await stoch_run(symbol)

    assert result is not None
    assert 'symbol' in result and result['symbol'] == symbol
    assert 'agent_name' in result and result['agent_name'] == agent_name
    assert 'verdict' in result
    assert 'value' in result
    assert 'details' in result
    assert 'k' in result['details']
    assert 'd' in result['details']

    assert result.get('error') is None, f"Agent returned error: {result.get('error')}"

    assert pytest.approx(result['details']['k'], abs=0.1) == last_k
    assert pytest.approx(result['details']['d'], abs=0.1) == last_d

    assert result['verdict'] == expected_verdict, \
        f"Expected verdict '{expected_verdict}' for neutral zone, got '{result['verdict']}'. Details: {result.get('details')}"

    mock_fetch_ohlcv.assert_awaited_once_with(symbol)
    mock_get_redis.assert_awaited_once()
    mock_redis_instance.get.assert_awaited_once_with(f"{agent_name}:{symbol}")
    if result.get('verdict') not in ['ERROR', 'NO_DATA']:
        mock_redis_instance.set.assert_awaited_once()
    else:
        mock_redis_instance.set.assert_not_awaited()

    mock_get_tracker.assert_called_once()
    mock_tracker_instance.update_agent_status.assert_awaited_once()

# Optional: Add tests for edge cases
# - Not enough data periods
# - fetch_ohlcv_series returns None or empty DataFrame
# - Division by zero in calculation (e.g., High = Low for all recent periods)
# - Redis get/set failures
