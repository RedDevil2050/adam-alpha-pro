import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import pandas as pd
import numpy as np
from unittest.mock import AsyncMock, patch, MagicMock
# Import the agent's run function
from backend.agents.technical.rsi_agent import run as rsi_run

agent_name = "rsi_agent"

@pytest.mark.asyncio
# Patch dependencies
@patch('backend.agents.decorators.get_tracker')
@patch('backend.agents.decorators.get_redis_client')
@patch('backend.utils.data_provider.fetch_price_series') # Correct patch target
async def test_rsi_agent_oversold(
    mock_fetch_prices,
    mock_get_redis,
    mock_get_tracker
):
    # --- Mock Configuration ---
    symbol = "TEST_RSI_OS"
    rsi_period = 14 # Default RSI period
    num_periods = rsi_period + 50 # Need enough data for calculation + stability

    # Create price data simulating an oversold condition (strong downward moves)
    prices = np.linspace(150, 100, num_periods) # General downward trend
    # Add noise
    prices += np.random.normal(0, 1.5, num_periods)
    # Ensure the last period reflects a low RSI
    # (More precise data generation might be needed for exact RSI values)
    price_series = pd.Series(prices, index=pd.date_range(end='2025-05-01', periods=num_periods, freq='D'))

    # Calculate expected RSI (simplified for testing, real calculation is complex)
    # For testing, we'll focus on the verdict based on expected range
    # delta = price_series.diff()
    # gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
    # loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
    # rs = gain / loss
    # expected_rsi = 100 - (100 / (1 + rs))
    # latest_expected_rsi = expected_rsi.iloc[-1]
    # For this test, we'll just assert the verdict assuming the data generates RSI < 30

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
    expected_verdict = "OVERSOLD" # Assuming RSI < 30
    # Confidence might vary based on how close to 0 RSI is
    # Let's assume a reasonable confidence for being below 30
    expected_confidence_min = 0.7 # Minimum expected confidence for oversold

    # --- Run Agent ---
    result = await rsi_run(symbol)

    # --- Assertions ---
    assert result['symbol'] == symbol
    # Expect the class name, not the module-level variable
    assert result['agent_name'] == 'RSIAgent'
    # assert result['agent_name'] == agent_name # Original assertion
    assert result['verdict'] == expected_verdict
    # Check that the calculated RSI ('value') is below the oversold threshold (default 30)
    assert 'value' in result
    assert isinstance(result['value'], (float, int))
    assert result['value'] < 30 # Check if RSI is indeed oversold
    assert result['confidence'] >= expected_confidence_min
    assert result.get('error') is None

    # Check details
    assert 'details' in result
    details = result['details']
    assert 'rsi' in details
    assert details['rsi'] == pytest.approx(result['value'])
    assert 'period' in details
    assert details['period'] == rsi_period

    # --- Verify Mocks ---
    mock_fetch_prices.assert_awaited_once()
    mock_get_redis.assert_awaited_once()
    mock_redis_instance.get.assert_awaited_once()
    mock_redis_instance.set.assert_awaited_once()
    mock_get_tracker.assert_called_once()
    mock_tracker_instance.update_agent_status.assert_awaited_once()
