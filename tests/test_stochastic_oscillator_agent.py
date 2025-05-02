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
    num_periods = k_window + d_window + 50 # Ensure enough data

    # Create price data simulating K crossing below D in overbought territory
    # 1. Strong uptrend to get K and D high
    prices = np.linspace(100, 150, num_periods - 5)
    # 2. Plateau or slight dip at the end to cause K to cross below D
    end_prices = np.array([150, 149.5, 149, 148.5, 148])
    prices = np.concatenate((prices, end_prices))

    # Generate OHLC based on prices, ensuring close is near high initially, then dips
    highs = prices + np.random.uniform(0.1, 0.5, num_periods) # Highs slightly above price
    lows = prices - np.random.uniform(0.1, 0.5, num_periods)  # Lows slightly below price
    closes = prices.copy()
    # Make final closes slightly lower than highs to simulate downturn
    closes[-5:] = lows[-5:] + np.random.uniform(0.05, 0.15, 5) # Close near low at the very end

    # Ensure highs >= closes >= lows
    highs = np.maximum(highs, closes)
    lows = np.minimum(lows, closes)

    # Create DataFrame matching fetch_ohlcv_series output
    ohlcv_df = pd.DataFrame({
        'high': highs,
        'low': lows,
        'close': closes,
        'open': closes - np.random.uniform(-0.1, 0.1, num_periods), # Dummy open near close
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
    # Expecting K crossing below D after being overbought (>80)
    expected_verdict = "AVOID"

    # --- Run Agent ---
    result = await stoch_run(symbol)

    # --- Assertions ---
    assert result['symbol'] == symbol
    assert result['agent_name'] == agent_name # Use agent_name variable
    # Add failure message for easier debugging
    assert result['verdict'] == expected_verdict, f"Expected {expected_verdict}, got {result['verdict']}. Details: {result.get('details')}"
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
    mock_get_redis.assert_awaited_once()
    mock_redis_instance.get.assert_awaited_once()
    # Set should be awaited only if verdict is not ERROR/NO_DATA
    if result.get('verdict') not in ['ERROR', 'NO_DATA']:
        mock_redis_instance.set.assert_awaited_once()
    else:
        mock_redis_instance.set.assert_not_awaited()
    # Tracker update is now handled by the decorator, check get_tracker call
    mock_get_tracker.assert_called_once()
    # Cannot easily assert await on tracker.update as it's called within decorator
