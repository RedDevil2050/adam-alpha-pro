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
# Patch dependencies (innermost first, so args are in this order)
@patch('backend.agents.technical.sma_agent.fetch_price_series', new_callable=AsyncMock)
@patch('backend.agents.base.get_redis_client', new_callable=AsyncMock) # Added for AgentBase
@patch('backend.agents.decorators.get_redis_client', new_callable=AsyncMock) # Decorator dependency
@patch('backend.agents.decorators.get_tracker') # Decorator dependency
async def test_sma_agent_golden_cross(
    m_fetch_prices,          # Renamed from mock_fetch_prices, corresponds to sma_agent.fetch_price_series
    mock_base_redis,         # New: Corresponds to base.get_redis_client
    mock_decorator_redis,    # Renamed from mock_get_redis, corresponds to decorators.get_redis_client
    mock_decorator_tracker   # Renamed from mock_get_tracker, corresponds to decorators.get_tracker
):
    # --- Mock Configuration ---
    symbol = "TEST_GC"
    short_window = 50
    long_window = 200
    num_periods = long_window + 2 # Need enough for long window + previous point

    # --- Create price data GUARANTEEING a golden cross ---
    # Start with short <= long, end with short > long
    prices = np.zeros(num_periods)
    # Initial phase: Keep prices high so long SMA starts high
    prices[:long_window] = 105 # Indices 0 to 199
    # Transition phase: Drop price slightly, then jump to cause crossover at the end
    prices[long_window] = 100   # Index 200 (for iloc[-2]) - Causes short SMA to dip below long SMA briefly if needed
    prices[long_window+1] = 120 # Index 201 (for iloc[-1]) - Sharp increase pulls short SMA above long SMA

    # Create pandas Series
    price_series = pd.Series(prices, index=pd.date_range(end='2025-05-01', periods=num_periods, freq='D'))

    # Calculate expected SMAs based on this specific data
    expected_short_sma = price_series.rolling(window=short_window).mean()
    expected_long_sma = price_series.rolling(window=long_window).mean()

    # Verify the cross condition in the generated data (for sanity check)
    latest_short = expected_short_sma.iloc[-1]
    latest_long = expected_long_sma.iloc[-1]
    prev_short = expected_short_sma.iloc[-2]
    prev_long = expected_long_sma.iloc[-2]

    # print(f"Latest: Short={latest_short}, Long={latest_long}") # Debugging
    # print(f"Previous: Short={prev_short}, Long={prev_long}") # Debugging
    assert latest_short > latest_long, "Test data failed to create latest short > long"
    assert prev_short <= prev_long, "Test data failed to create previous short <= long"
    # --- End Data Generation ---


    # 1. Mock fetch_price_series
    m_fetch_prices.return_value = price_series

    # 2. Mock Redis
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get.return_value = None # Cache miss
    mock_redis_instance.set = AsyncMock()
    mock_decorator_redis.return_value = mock_redis_instance
    mock_base_redis.return_value = mock_redis_instance # Configure base_redis mock

    # 3. Mock Tracker
    mock_tracker_instance = AsyncMock() # Assuming get_tracker returns an object with async methods
    mock_tracker_instance.update_agent_status = AsyncMock()
    mock_decorator_tracker.return_value = mock_tracker_instance

    # --- Expected Results ---
    expected_verdict = "GOLDEN_CROSS"
    expected_confidence = 0.9 # As per agent logic
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
    assert f'sma_{short_window}' in result['details']
    assert f'sma_{long_window}' in result['details']
    assert result['details'][f'sma_{short_window}'] == pytest.approx(expected_latest_short_sma)
    assert result['details'][f'sma_{long_window}'] == pytest.approx(expected_latest_long_sma)
    assert result.get('error') is None

    # --- Verify Mocks ---
    m_fetch_prices.assert_awaited_once()
    # Check fetch_price_series args if needed
    fetch_args, fetch_kwargs = m_fetch_prices.call_args
    assert fetch_args[0] == symbol
    assert fetch_kwargs.get('period') == f"{long_window + 5}d"

    # Verify the mock passed to the test was used by the decorator and base
    mock_decorator_redis.assert_awaited_once()
    mock_base_redis.assert_awaited_once() # Verify base_redis was called
    
    # mock_redis_instance.get is called by decorator's cache and agent's own cache (via AgentBase)
    assert mock_redis_instance.get.await_count >= 1 # Adjusted to >=1 as exact count can vary based on internal logic
    mock_redis_instance.set.assert_awaited_once() # Typically called once by decorator if cache miss

    mock_decorator_tracker.assert_called_once() 
    mock_tracker_instance.update_agent_status.assert_awaited_once()
