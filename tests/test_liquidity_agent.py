import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import numpy as np
from unittest.mock import AsyncMock, patch
# Correct import path based on file search
from backend.agents.market.liquidity_agent import run as liquidity_run 

agent_name = "liquidity_agent"

@pytest.mark.asyncio
# Patch dependencies (innermost first)
@patch('backend.agents.decorators.get_tracker') # Decorator dependency
@patch('backend.agents.decorators.get_redis_client') # Decorator dependency
# Correct patch targets to where functions are *used* in the agent module
@patch('backend.agents.market.liquidity_agent.fetch_volume_series') 
@patch('backend.agents.market.liquidity_agent.fetch_price_series')
async def test_liquidity_agent_high_liquidity(
    mock_fetch_prices, 
    mock_fetch_volumes, 
    mock_get_redis, 
    mock_get_tracker
):
    # --- Mock Configuration ---
    symbol = "TEST_SYMBOL"
    min_days = 20
    num_data_points = 30 # Provide more than min_days

    # 1. Mock fetch_price_series
    mock_prices = list(np.linspace(95, 105, num_data_points))
    mock_fetch_prices.return_value = mock_prices
    last_price = mock_prices[-1]

    # 2. Mock fetch_volume_series (high recent volume)
    # Average volume for first 20 days (used for avg calc) = 100k
    # Last volume = 400k (high relative volume)
    mock_volumes = [100000] * num_data_points 
    mock_volumes[-1] = 400000 # Make last volume high
    mock_fetch_volumes.return_value = mock_volumes
    last_volume = mock_volumes[-1]
    # Calculate expected avg based on the last 20 points of mock data
    expected_avg_vol = np.mean(mock_volumes[-min_days:]) 

    # 3. Mock Redis
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get.return_value = None # Cache miss
    mock_redis_instance.set = AsyncMock()
    mock_get_redis.return_value = mock_redis_instance

    # 4. Mock Tracker
    mock_tracker_instance = AsyncMock()
    mock_tracker_instance.update_agent_status = AsyncMock()
    mock_get_tracker.return_value = mock_tracker_instance

    # --- Expected Calculations ---
    # relative_volume = last_volume / expected_avg_vol
    # volume_score = min(1.0, relative_volume / 3.0)
    # liquidity_score = volume_score
    # Based on the mock data: avg = 115k, rel_vol = 3.478, score = 1.0
    expected_score = 1.0 
    expected_verdict = "HIGH_LIQUIDITY"
    expected_confidence = 0.8
    expected_rel_vol = last_volume / expected_avg_vol
    expected_turnover = last_volume * last_price

    # --- Run Agent ---
    result = await liquidity_run(symbol)

    # --- Assertions ---
    assert result['symbol'] == symbol
    assert result['agent_name'] == agent_name
    assert result['verdict'] == expected_verdict
    assert result['confidence'] == pytest.approx(expected_confidence)
    assert result['value'] == pytest.approx(expected_score) # Value is the liquidity score
    assert result.get('error') is None

    # Check details
    assert 'details' in result
    details = result['details']
    # Use pytest.approx for float comparisons
    assert details['avg_daily_volume_20d'] == pytest.approx(expected_avg_vol)
    assert details['last_volume'] == last_volume
    assert details['relative_volume_vs_20d_avg'] == pytest.approx(expected_rel_vol)
    assert details['last_turnover'] == pytest.approx(expected_turnover)

    # --- Verify Mocks ---
    mock_fetch_prices.assert_awaited_once_with(symbol)
    mock_fetch_volumes.assert_awaited_once_with(symbol)
    mock_get_redis.assert_awaited_once()
    mock_redis_instance.get.assert_awaited_once()
    mock_redis_instance.set.assert_awaited_once() # Should cache on success
    mock_get_tracker.assert_called_once() # Check if tracker was fetched
    mock_tracker_instance.update_agent_status.assert_awaited_once() # Check status update
