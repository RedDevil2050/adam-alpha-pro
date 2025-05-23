import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import pandas as pd
import numpy as np
import datetime # Add datetime import
from unittest.mock import AsyncMock, patch, MagicMock
# Import the agent's run function
from backend.agents.technical.rsi_agent import run as rsi_run, agent_name # Import agent_name

# agent_name = "rsi_agent" # Use imported name

@pytest.mark.asyncio
# Patch dependencies in reverse order
# Patch datetime used by the agent
@patch('backend.agents.technical.rsi_agent.datetime')
@patch('backend.agents.decorators.get_tracker')
@patch('backend.agents.decorators.get_redis_client', new_callable=AsyncMock)
@patch('backend.agents.technical.rsi_agent.fetch_ohlcv_series', new_callable=AsyncMock)
@patch('backend.agents.base.get_redis_client', new_callable=AsyncMock)  # Patch for AgentBase
async def test_rsi_agent_oversold(
    mock_base_get_redis_client, # New mock for base
    mock_fetch_ohlcv, # Renamed mock
    mock_get_redis_decorator, # Renamed to reflect it mocks the decorator's get_redis_client
    mock_get_tracker,
    mock_datetime_in_agent # This is the mock for 'backend.agents.technical.rsi_agent.datetime'
):
    # --- Mock Configuration ---
    symbol = "TEST_RSI_OS"
    
    # Use real datetime for test setup, but mock what the agent sees
    real_datetime_date_class = datetime.date
    real_datetime_timedelta_class = datetime.timedelta
    mock_today_date_object = real_datetime_date_class(2025, 5, 2)

    # Configure datetime.date.today() as seen by the agent
    # The agent calls datetime.date.today()
    mock_datetime_in_agent.date.today.return_value = mock_today_date_object

    # Ensure timedelta and datetime.datetime are available if the agent uses them via the mocked datetime module
    mock_datetime_in_agent.timedelta = real_datetime_timedelta_class
    mock_datetime_in_agent.datetime = datetime.datetime # Assigns the actual datetime module to this attribute of the mock

    rsi_period = 14 # Default RSI period
    num_periods = rsi_period + 50 # Need enough data for calculation + stability

    # Create price data simulating an oversold condition (strong downward moves)
    # Start with a general downward trend
    prices = np.linspace(150, 110, num_periods)
    # Add noise
    prices += np.random.normal(0, 1.0, num_periods)
    # Make the last few periods drop more sharply to ensure oversold
    prices[-rsi_period:] -= np.linspace(0, 10, rsi_period) # Steeper drop at the end

    # Create DataFrame matching fetch_ohlcv_series output (needs 'close' column)
    price_df = pd.DataFrame({
        'close': prices,
        'open': prices - np.random.uniform(0, 1, num_periods), # Add dummy open/high/low/vol
        'high': prices + np.random.uniform(0, 1, num_periods),
        'low': prices - np.random.uniform(0, 1, num_periods),
        'volume': np.random.randint(1000, 5000, num_periods)
    }, index=pd.date_range(end='2025-05-01', periods=num_periods, freq='D'))


    # 1. Mock fetch_ohlcv_series
    mock_fetch_ohlcv.return_value = price_df

    # Shared Redis instance for all mocks that need it
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get = AsyncMock(return_value=None)  # Cache miss for decorator
    mock_redis_instance.set = AsyncMock()

    # Configure the decorator's get_redis_client mock
    mock_get_redis_decorator.return_value = mock_redis_instance

    # Configure the base agent's get_redis_client mock
    mock_base_get_redis_client.return_value = mock_redis_instance 

    # 3. Mock Tracker instance and configure the factory mock
    mock_tracker_instance = AsyncMock() # Use AsyncMock for async method
    mock_tracker_instance.update_agent_status = AsyncMock()
    # Ensure get_tracker returns an AsyncMock if its methods are awaited
    # If get_tracker itself is a coroutine, it should be new_callable=AsyncMock
    # If get_tracker returns an object with async methods, its return_value needs to be an AsyncMock or have AsyncMock methods.
    # Based on the error, the issue is likely with how get_redis_client is mocked or used within the agent/decorator,
    # but let's ensure get_tracker is also correctly async if needed.
    # For now, the primary fix is for get_redis_client.
    mock_get_tracker.return_value = mock_tracker_instance 

    # --- Expected Results ---
    # Based on the agent logic, RSI < 30 (default) triggers BUY (oversold)
    expected_verdict = "BUY" # Assuming RSI < 30
    expected_confidence_min = 0.7 # Minimum expected confidence for oversold (BUY)

    # --- Run Agent ---
    # Pass symbol only, decorator handles agent_outputs if not provided
    result = await rsi_run(symbol)

    # --- Assertions ---
    assert result['symbol'] == symbol
    # Assert agent name using the imported variable
    assert result['agent_name'] == agent_name
    # Check for potential errors before asserting verdict
    if result.get('error'):
        pytest.fail(f"Agent returned an error: {result['error']}")
    assert result['verdict'] == expected_verdict
    assert 'value' in result # RSI value
    # Check confidence range if verdict is BUY
    if result['verdict'] == 'BUY':
        assert result['confidence'] >= expected_confidence_min
    assert result.get('error') is None

    # --- Verify Mocks ---
    # Calculate expected dates based on mocked today
    end_date = mock_today_date_object # Use the object used for mocking
    start_date = end_date - real_datetime_timedelta_class(days=365) # Use real timedelta for test calculation
    mock_fetch_ohlcv.assert_awaited_once_with(symbol, start_date=start_date, end_date=end_date) # Check symbol and date args
    mock_get_redis_decorator.assert_awaited_once() # Verify the factory function was awaited
    mock_base_get_redis_client.assert_awaited_once() # AgentBase's redis client factory
    
    # The decorator calls .get() once. The agent base also calls .get() once.
    # Both use the same mock_redis_instance.get
    assert mock_redis_instance.get.await_count == 2
    if result.get('verdict') not in ['NO_DATA', 'ERROR', None]:
        assert mock_redis_instance.set.await_count == 2 # Expecting set to be called twice
    else:
        mock_redis_instance.set.assert_not_awaited()
    mock_get_tracker.assert_called_once() # Tracker factory
    mock_tracker_instance.update_agent_status.assert_awaited_once() # Tracker update method
