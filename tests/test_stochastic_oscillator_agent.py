import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import pandas as pd
import numpy as np
from unittest.mock import AsyncMock, patch, MagicMock
# Import the agent's run function
# Assuming the agent file is indeed named stochastic_oscillator_agent.py
from backend.agents.technical.stochastic_oscillator_agent import run as stoch_run

agent_name = "stochastic_oscillator_agent" # Match agent's name

@pytest.mark.asyncio
# Patch dependencies
@patch('backend.agents.decorators.get_tracker')
@patch('backend.utils.cache_utils.get_redis_client') # Correct redis patch target
@patch('backend.agents.technical.stochastic_oscillator_agent.fetch_ohlcv_series') # Correct patch target
async def test_stochastic_oscillator_overbought(
    mock_fetch_ohlcv, # Renamed mock
    mock_get_redis,
    mock_get_tracker,
    monkeypatch
):
    # --- Mock Configuration ---
    symbol = "TEST_STOCH_OB"
    k_window = 14 # Default K window
    d_window = 3  # Default D window
    # Agent uses Fast Stochastic (%K = raw, %D = SMA(%K, 3))
    num_periods = k_window + d_window + 50 # Ensure enough data

    # Create price data simulating an overbought condition (close near high)
    prices = np.linspace(100, 150, num_periods) # General upward trend
    prices += np.random.normal(0, 1.5, num_periods)
    # Force the last close to be near the high of the recent period
    highs = prices + np.random.uniform(0, 2, num_periods)
    lows = prices - np.random.uniform(0, 2, num_periods)
    closes = highs - np.random.uniform(0, 0.5, num_periods) # Close near high

    # Ensure last close is strictly less than last high for calculation stability
    highs[-1] = max(highs[-1], closes[-1] + 0.01)
    # Ensure last low is strictly less than last close
    lows[-1] = min(lows[-1], closes[-1] - 0.01)


    # Create DataFrame matching fetch_ohlcv_series output
    ohlcv_df = pd.DataFrame({
        'high': highs,
        'low': lows,
        'close': closes,
        'open': closes - np.random.uniform(0, 1, num_periods), # Dummy open
        'volume': np.random.randint(1000, 5000, num_periods) # Dummy volume
    }, index=pd.date_range(end='2025-05-01', periods=num_periods, freq='D'))


    # 1. Mock fetch_ohlcv_series
    mock_fetch_ohlcv.return_value = ohlcv_df

    # 2. Mock Redis
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get.return_value = None # Cache miss
    mock_redis_instance.set = AsyncMock()
    mock_get_redis.return_value = mock_redis_instance

    # 3. Mock Tracker
    mock_tracker_instance = AsyncMock()
    mock_tracker_instance.update = AsyncMock() # Match agent usage
    # Patch the specific tracker instance used in the agent module
    monkeypatch.setattr('backend.agents.technical.stochastic_oscillator_agent.tracker', mock_tracker_instance)


    # --- Expected Results ---
    # Agent logic: BUY if K crosses above D, AVOID if K crosses below D, HOLD otherwise.
    # This test aims for overbought, but the agent logic is crossover-based.
    # Let's adjust the test to check for a SELL signal (K crossing below D in overbought territory)
    # Modify data to create a K < D crossover after being high
    ohlcv_df['k'] = 100 * ((ohlcv_df['close'] - ohlcv_df['low'].rolling(k_window).min()) /
                           (ohlcv_df['high'].rolling(k_window).max() - ohlcv_df['low'].rolling(k_window).min()))
    ohlcv_df['d'] = ohlcv_df['k'].rolling(d_window).mean()

    # Force a K < D crossover at the end after being high
    # Find the last valid index where k and d are calculated
    valid_idx = ohlcv_df[['k', 'd']].last_valid_index()
    if valid_idx is not None and valid_idx != ohlcv_df.index[-1]:
         idx_loc = ohlcv_df.index.get_loc(valid_idx)
         if idx_loc >= 1: # Need at least two points
             # Make previous K > D
             ohlcv_df.loc[ohlcv_df.index[idx_loc-1], 'k'] = 85
             ohlcv_df.loc[ohlcv_df.index[idx_loc-1], 'd'] = 80
             # Make current K < D
             ohlcv_df.loc[valid_idx, 'k'] = 75
             ohlcv_df.loc[valid_idx, 'd'] = 80
             # Recalculate D based on forced K for the last point
             ohlcv_df['d'] = ohlcv_df['k'].rolling(d_window).mean()


    expected_verdict = "AVOID" # Expecting K crossing below D
    # expected_confidence = 0.0 # Agent sets confidence to 0.0 for AVOID

    # --- Run Agent ---
    result = await stoch_run(symbol)

    # --- Assertions ---
    assert result['symbol'] == symbol
    assert result['agent_name'] == agent_name
    assert result['verdict'] == expected_verdict
    # assert result['confidence'] == expected_confidence # Check confidence for AVOID
    assert 'value' in result # K - D difference
    assert 'details' in result
    assert 'k' in result['details']
    assert 'd' in result['details']
    # Check if K < D in details for AVOID verdict
    if result['verdict'] == 'AVOID':
        assert result['details']['k'] < result['details']['d']
    assert result.get('error') is None

    # --- Verify Mocks ---
    mock_fetch_ohlcv.assert_awaited_once()
    # Check args if needed: mock_fetch_ohlcv.assert_awaited_once_with(symbol, start_date=..., end_date=...)
    mock_get_redis.assert_awaited_once()
    mock_redis_instance.get.assert_awaited_once()
    mock_redis_instance.set.assert_awaited_once()
    # mock_tracker_instance.update.assert_called_once() # Verify tracker update
