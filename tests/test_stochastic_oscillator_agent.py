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
@patch('backend.agents.decorators.get_redis_client')
@patch('backend.utils.data_provider.fetch_price_series') # Correct patch target
async def test_stochastic_oscillator_overbought(
    mock_fetch_prices,
    mock_get_redis,
    mock_get_tracker
):
    # --- Mock Configuration ---
    symbol = "TEST_STOCH_OB"
    k_window = 14 # Default K window
    d_window = 3  # Default D window
    k_smoothing = 3 # Default K smoothing (Full Stochastic)
    num_periods = k_window + k_smoothing + d_window + 50 # Ensure enough data

    # Create price data simulating an overbought condition (strong upward moves, close near high)
    prices = np.linspace(100, 150, num_periods) # General upward trend
    prices += np.random.normal(0, 1.5, num_periods)
    # Force the last close to be near the high of the recent period
    prices[-1] = prices[-(k_window):].max() - np.random.uniform(0, 1) # Close near high

    price_series = pd.Series(prices, index=pd.date_range(end='2025-05-01', periods=num_periods, freq='D'))

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
    expected_verdict = "OVERBOUGHT" # Assuming %K > 80
    expected_confidence_min = 0.7 # Minimum expected confidence for overbought

    # --- Run Agent ---
    result = await stoch_run(symbol)

    # --- Assertions ---
    assert result['symbol'] == symbol
    assert result['agent_name'] == agent_name
    assert result['verdict'] == expected_verdict
    # Check that the calculated %K ('value') is above the overbought threshold (default 80)
    assert 'value' in result
    assert isinstance(result['value'], (float, int))
    assert result['value'] > 80 # Check if %K is indeed overbought
    assert result['confidence'] >= expected_confidence_min
    assert result.get('error') is None

    # Check details
    assert 'details' in result
    details = result['details']
    assert 'k' in details
    assert 'd' in details
    assert details['k'] == pytest.approx(result['value'])
    assert isinstance(details['d'], (float, int))
    # Optionally check D value range if needed
    # assert details['d'] > 70 # Example check for D in overbought territory

    # --- Verify Mocks ---
    mock_fetch_prices.assert_awaited_once()
    mock_get_redis.assert_awaited_once()
    mock_redis_instance.get.assert_awaited_once()
    mock_redis_instance.set.assert_awaited_once()
    mock_get_tracker.assert_called_once()
    mock_tracker_instance.update_agent_status.assert_awaited_once()
