import sys, os
import datetime
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

# Helper to create minimal OHLCV data
def create_minimal_ohlcv(periods=20):
    prices = np.linspace(100, 105, periods)
    return pd.DataFrame({
        'high': prices + 0.5,
        'low': prices - 0.5,
        'close': prices,
        'open': prices,
        'volume': np.random.randint(1000, 5000, periods)
    }, index=pd.date_range(end='2025-05-01', periods=periods, freq='D'))

@pytest.mark.asyncio
# Patch dependencies
@patch('backend.agents.decorators.get_tracker')
# Correct patch target: where get_redis_client is IMPORTED/USED in the agent module
@patch('backend.agents.technical.stochastic_oscillator_agent.get_redis_client')
# Patch the pta object imported within the agent module
@patch('backend.agents.technical.stochastic_oscillator_agent.pta')
@patch('backend.agents.technical.stochastic_oscillator_agent.fetch_ohlcv_series') # Correct patch target
async def test_stochastic_oscillator_overbought_crossover(
    mock_fetch_ohlcv,
    mock_pta, # Patched pta object
    mock_get_redis,
    mock_get_tracker,
):
    """
    Test Stochastic Oscillator agent for K crossing below D in the overbought zone.
    Refactored to mock the calculation result directly.
    """
    symbol = "TEST_STOCH_OB_CROSS"
    agent_name = "stochastic_oscillator_agent"
    k_col = 'STOCHk_14_3_3' # Adjust if agent uses different column names
    d_col = 'STOCHd_14_3_3'

    # --- Mock Configuration ---
    # 1. Mock fetch_ohlcv_series to return minimal valid data
    mock_fetch_ohlcv.return_value = create_minimal_ohlcv()

    # 2. Configure the mock pta object's stoch method
    mock_stoch_output = pd.DataFrame({
        k_col: [85.0, 78.0], # K was above D (85 > 82), now below (78 < 81)
        d_col: [82.0, 81.0]  # Both values near/in overbought zone (>80)
    }, index=pd.date_range(end='2025-05-01', periods=2, freq='D'))
    mock_pta.stoch.return_value = mock_stoch_output

    # 3. Mock Redis
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get.return_value = None
    mock_redis_instance.set = AsyncMock()
    mock_get_redis.return_value = mock_redis_instance

    # 4. Mock Tracker
    mock_tracker_instance = AsyncMock()
    mock_tracker_instance.update_agent_status = AsyncMock()
    mock_get_tracker.return_value = mock_tracker_instance

    # --- Expected Results ---
    expected_verdict = "AVOID" # Or "SELL"
    expected_k = mock_stoch_output[k_col].iloc[-1]
    expected_d = mock_stoch_output[d_col].iloc[-1]

    # --- Run Agent ---
    result = await stoch_run(symbol)

    # --- Assertions ---
    assert result is not None
    assert result.get('error') is None, f"Agent returned error: {result.get('error')}"
    assert result['symbol'] == symbol
    assert result['agent_name'] == agent_name
    assert result['verdict'] == expected_verdict
    assert 'details' in result
    assert pytest.approx(result['details']['k']) == expected_k
    assert pytest.approx(result['details']['d']) == expected_d
    assert result['details']['k'] < result['details']['d'] # Verify crossover direction in result
    assert result['details']['d'] > OVERBOUGHT_THRESHOLD # Verify it happened in OB zone

    # --- Verify Mocks ---
    mock_fetch_ohlcv.assert_awaited_once() # Check it was called, args checked in neutral test
    # Verify pta.stoch was called (via the mocked pta object)
    mock_pta.stoch.assert_called_once()
    # We can optionally check args passed to mock_pta.stoch if needed
    # from unittest.mock import ANY
    # mock_pta.stoch.assert_called_once_with(close=ANY, high=ANY, low=ANY, k=14, d=3, smooth_k=3)
    mock_get_redis.assert_awaited_once()
    mock_redis_instance.get.assert_awaited_once_with(f"{agent_name}:{symbol}")
    mock_redis_instance.set.assert_awaited_once()
    mock_get_tracker.assert_called_once()
    mock_tracker_instance.update_agent_status.assert_awaited_once()


# Add tests for other scenarios (oversold crossover, neutral, etc.)
@pytest.mark.asyncio
@patch('backend.agents.decorators.get_tracker')
@patch('backend.agents.technical.stochastic_oscillator_agent.get_redis_client')
# Patch the pta object imported within the agent module
@patch('backend.agents.technical.stochastic_oscillator_agent.pta')
@patch('backend.agents.technical.stochastic_oscillator_agent.fetch_ohlcv_series')
async def test_stochastic_oscillator_oversold_crossover(
    mock_fetch_ohlcv,
    mock_pta, # Patched pta object
    mock_get_redis,
    mock_get_tracker,
):
    """
    Test Stochastic Oscillator agent for K crossing above D in the oversold zone.
    Refactored to mock the calculation result directly.
    """
    symbol = "TEST_STOCH_OS_CROSS"
    agent_name = "stochastic_oscillator_agent"
    k_col = 'STOCHk_14_3_3'
    d_col = 'STOCHd_14_3_3'

    # --- Mock Configuration ---
    mock_fetch_ohlcv.return_value = create_minimal_ohlcv()

    # Configure the mock pta object's stoch method for OS crossover
    mock_stoch_output = pd.DataFrame({
        k_col: [15.0, 22.0], # K was below D (15 < 18), now above (22 > 19)
        d_col: [18.0, 19.0]  # Both values near/in oversold zone (<20)
    }, index=pd.date_range(end='2025-05-01', periods=2, freq='D'))
    mock_pta.stoch.return_value = mock_stoch_output

    mock_redis_instance = AsyncMock()
    mock_redis_instance.get.return_value = None
    mock_redis_instance.set = AsyncMock()
    mock_get_redis.return_value = mock_redis_instance

    mock_tracker_instance = AsyncMock()
    mock_tracker_instance.update_agent_status = AsyncMock()
    mock_get_tracker.return_value = mock_tracker_instance

    # --- Expected Results ---
    expected_verdict = "BUY"
    expected_k = mock_stoch_output[k_col].iloc[-1]
    expected_d = mock_stoch_output[d_col].iloc[-1]

    # --- Run Agent ---
    result = await stoch_run(symbol)

    # --- Assertions ---
    assert result is not None
    assert result.get('error') is None, f"Agent returned error: {result.get('error')}"
    assert result['symbol'] == symbol
    assert result['agent_name'] == agent_name
    assert result['verdict'] == expected_verdict
    assert 'details' in result
    assert pytest.approx(result['details']['k']) == expected_k
    assert pytest.approx(result['details']['d']) == expected_d
    assert result['details']['k'] > result['details']['d'] # Verify crossover direction
    assert result['details']['d'] < OVERSOLD_THRESHOLD # Verify it happened in OS zone

    # --- Verify Mocks ---
    mock_fetch_ohlcv.assert_awaited_once()
    # Verify pta.stoch was called
    mock_pta.stoch.assert_called_once()
    mock_get_redis.assert_awaited_once()
    mock_redis_instance.get.assert_awaited_once_with(f"{agent_name}:{symbol}")
    mock_redis_instance.set.assert_awaited_once()
    mock_get_tracker.assert_called_once()
    mock_tracker_instance.update_agent_status.assert_awaited_once()


# Optional: Add a test for a neutral scenario (K/D between 20-80)
@pytest.mark.asyncio
@patch('backend.agents.decorators.get_tracker')
@patch('backend.agents.technical.stochastic_oscillator_agent.get_redis_client')
# Patch the pta object imported within the agent module
@patch('backend.agents.technical.stochastic_oscillator_agent.pta')
@patch('backend.agents.technical.stochastic_oscillator_agent.fetch_ohlcv_series')
async def test_stochastic_oscillator_neutral(
    mock_fetch_ohlcv,
    mock_pta, # Patched pta object
    mock_get_redis,
    mock_get_tracker,
):
    """
    Test Stochastic Oscillator agent for K and D in the neutral zone (20-80).
    Refactored to mock the calculation result directly.
    """
    symbol = "TEST_STOCH_NEUTRAL"
    agent_name = "stochastic_oscillator_agent"
    k_col = 'STOCHk_14_3_3'
    d_col = 'STOCHd_14_3_3'

    # --- Mock Configuration ---
    mock_fetch_ohlcv.return_value = create_minimal_ohlcv()

    # Configure the mock pta object's stoch method for neutral zone
    mock_stoch_output = pd.DataFrame({
        k_col: [50.0, 55.0], # K and D values within the neutral zone (20-80)
        d_col: [48.0, 52.0]
    }, index=pd.date_range(end='2025-05-01', periods=2, freq='D'))
    mock_pta.stoch.return_value = mock_stoch_output

    mock_redis_instance = AsyncMock()
    mock_redis_instance.get.return_value = None
    mock_redis_instance.set = AsyncMock()
    mock_get_redis.return_value = mock_redis_instance

    mock_tracker_instance = AsyncMock()
    mock_tracker_instance.update_agent_status = AsyncMock()
    mock_get_tracker.return_value = mock_tracker_instance

    # --- Expected Results ---
    expected_verdict = "HOLD"
    expected_k = mock_stoch_output[k_col].iloc[-1]
    expected_d = mock_stoch_output[d_col].iloc[-1]

    # --- Run Agent ---
    result = await stoch_run(symbol)

    # --- Assertions ---
    assert result is not None
    assert result.get('error') is None, f"Agent returned error: {result.get('error')}"
    assert result['symbol'] == symbol
    assert result['agent_name'] == agent_name
    assert result['verdict'] == expected_verdict
    assert 'details' in result
    assert pytest.approx(result['details']['k']) == expected_k
    assert pytest.approx(result['details']['d']) == expected_d
    # Assert K and D are within the neutral range in the result
    assert OVERSOLD_THRESHOLD <= result['details']['k'] <= OVERBOUGHT_THRESHOLD
    assert OVERSOLD_THRESHOLD <= result['details']['d'] <= OVERBOUGHT_THRESHOLD

    # --- Verify Mocks ---
    # Calculate expected dates (1 year back from today, May 2, 2025)
    end_date = datetime.date(2025, 5, 2)
    start_date = end_date - datetime.timedelta(days=365)
    mock_fetch_ohlcv.assert_awaited_once_with(symbol, start_date=start_date, end_date=end_date)

    # Verify pta.stoch was called
    mock_pta.stoch.assert_called_once()

    mock_get_redis.assert_awaited_once()
    mock_redis_instance.get.assert_awaited_once_with(f"{agent_name}:{symbol}")
    mock_redis_instance.set.assert_awaited_once()
    mock_get_tracker.assert_called_once()
    mock_tracker_instance.update_agent_status.assert_awaited_once()

# Optional: Add tests for edge cases
# - Not enough data periods
# - fetch_ohlcv_series returns None or empty DataFrame
# - Division by zero in calculation (e.g., High = Low for all recent periods)
# - Redis get/set failures
