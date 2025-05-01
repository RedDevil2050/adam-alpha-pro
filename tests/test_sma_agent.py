import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import pandas as pd
import numpy as np
from unittest.mock import AsyncMock, patch, MagicMock
# Import the agent's run function
from backend.agents.technical.sma_agent import run as sma_run

agent_name = "sma_agent"

@pytest.mark.asyncio
# Patch dependencies (innermost first)
@patch('backend.agents.decorators.get_tracker') # Decorator dependency
@patch('backend.agents.decorators.get_redis_client') # Decorator dependency
@patch('backend.agents.technical.sma_agent.fetch_price_series')
async def test_sma_agent_golden_cross(
    mock_fetch_prices,
    mock_get_redis,
    mock_get_tracker
):
    # --- Mock Configuration ---
    symbol = "TEST_GC"
    short_window = 50
    long_window = 200
    num_periods = long_window + 2 # Need enough for long window + previous point

    # Create price data simulating a golden cross
    # Start with short SMA below long SMA, then make it cross above
    prices = np.linspace(100, 150, num_periods) # General upward trend
    # Introduce variation to make SMAs distinct
    prices += np.random.normal(0, 2, num_periods)
    # Ensure the cross happens at the end
    # Manually adjust last few points if needed to force the cross condition
    # For simplicity, we'll rely on the trend and check the calculated SMAs

    price_series = pd.Series(prices, index=pd.date_range(end='2025-05-01', periods=num_periods, freq='D'))

    # Calculate expected SMAs based on mock data (for verification)
    expected_short_sma = price_series.rolling(window=short_window).mean()
    expected_long_sma = price_series.rolling(window=long_window).mean()

    # Ensure the mock data *actually* creates a golden cross at the end
    # This requires manual adjustment or more sophisticated data generation
    # For this test, let's assume the generated data works, but refine if needed
    # We need:
    # latest_short > latest_long
    # prev_short <= prev_long

    # Adjust last two points to force a golden cross for the test
    # Make prev_short slightly below prev_long
    # Make latest_short slightly above latest_long
    temp_short_sma = price_series.rolling(window=short_window).mean()
    temp_long_sma = price_series.rolling(window=long_window).mean()
    idx = -1
    while idx > -len(price_series):
        # Ensure indices are valid before accessing
        if idx - 1 >= -len(price_series):
            prev_s = temp_short_sma.iloc[idx-1]
            prev_l = temp_long_sma.iloc[idx-1]
            curr_s = temp_short_sma.iloc[idx]
            curr_l = temp_long_sma.iloc[idx]
            if not (pd.isna(prev_s) or pd.isna(prev_l) or pd.isna(curr_s) or pd.isna(curr_l)):
                 if curr_s > curr_l and prev_s <= prev_l:
                     # Found a natural golden cross in generated data
                     break
                 # If near the end and no cross found, force it (crude adjustment)
                 if idx == -2:
                     # Force prev_short <= prev_long
                     price_series.iloc[idx-1] -= 5
                     # Force latest_short > latest_long
                     price_series.iloc[idx] += 5
                     # Recalculate expected SMAs after forcing
                     expected_short_sma = price_series.rolling(window=short_window).mean()
                     expected_long_sma = price_series.rolling(window=long_window).mean()
                     break
        else:
            # Should not happen with num_periods = long_window + 2, but handle defensively
            pytest.fail("Not enough data points to check for crossover")
            break
        idx -= 1


    # 1. Mock fetch_price_series
    mock_fetch_prices.return_value = price_series

    # 2. Mock Redis
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get.return_value = None # Cache miss
    mock_redis_instance.set = AsyncMock()
    mock_get_redis.return_value = mock_redis_instance

    # 3. Mock Tracker
    mock_tracker_instance = AsyncMock()
    mock_tracker_instance.update_agent_status = AsyncMock()
    mock_get_tracker.return_value = mock_tracker_instance

    # --- Expected Results ---
    expected_verdict = "GOLDEN_CROSS"
    expected_confidence = 0.9
    expected_latest_price = price_series.iloc[-1]
    expected_latest_short_sma = expected_short_sma.iloc[-1]
    expected_latest_long_sma = expected_long_sma.iloc[-1]

    # --- Run Agent ---
    result = await sma_run(symbol)

    # --- Assertions ---
    assert result['symbol'] == symbol
    assert result['agent_name'] == agent_name
    assert result['verdict'] == expected_verdict
    assert result['confidence'] == pytest.approx(expected_confidence)
    assert result['value'] == pytest.approx(expected_latest_price)
    assert result.get('error') is None

    # Check details
    assert 'details' in result
    details = result['details']
    assert details[f'sma_{short_window}'] == pytest.approx(expected_latest_short_sma)
    assert details[f'sma_{long_window}'] == pytest.approx(expected_latest_long_sma)
    assert details['short_window'] == short_window
    assert details['long_window'] == long_window

    # --- Verify Mocks ---
    mock_fetch_prices.assert_awaited_once()
    # Check symbol and period argument if needed
    call_args, call_kwargs = mock_fetch_prices.call_args
    assert call_args[0] == symbol
    assert 'period' in call_kwargs

    mock_get_redis.assert_awaited_once()
    mock_redis_instance.get.assert_awaited_once()
    mock_redis_instance.set.assert_awaited_once() # Should cache on success
    mock_get_tracker.assert_called_once() # Check if tracker was fetched
    mock_tracker_instance.update_agent_status.assert_awaited_once() # Check status update
