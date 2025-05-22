import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import pandas as pd
from unittest.mock import AsyncMock, patch, MagicMock # Added MagicMock
from backend.agents.technical.supertrend_agent import run as st_run
import datetime

@pytest.mark.asyncio
@patch('backend.agents.decorators.get_redis_client', new_callable=AsyncMock) # This mock is the second argument
@patch('backend.agents.decorators.get_tracker') # This mock is the first argument
async def test_supertrend_agent(mock_get_tracker_arg, mock_get_redis_arg, monkeypatch): # CORRECTED: Parameter order and names
    # mock_get_tracker_arg is for 'get_tracker' (MagicMock)
    # mock_get_redis_arg is for 'get_redis_client' (AsyncMock)
    # Mock data matching expected OHLCV structure
    dates = pd.to_datetime([datetime.date.today() - datetime.timedelta(days=x) for x in range(9, -1, -1)])
    prices = pd.DataFrame({
        'high': [10, 12, 11, 13, 12, 14, 13, 15, 14, 16],
        'low': [8, 9, 9, 10, 10, 11, 11, 12, 12, 13],
        'close': [9, 11, 10, 12, 11, 13, 12, 14, 13, 15],
        'open': [8.5, 10.5, 9.5, 11.5, 10.5, 12.5, 11.5, 13.5, 12.5, 14.5],
        'volume': [1000] * 10
    }, index=dates)

    # Mock fetch_ohlcv_series within the agent's module
    mock_fetch = AsyncMock(return_value=prices)
    monkeypatch.setattr('backend.agents.technical.supertrend_agent.fetch_ohlcv_series', mock_fetch)

    # Mock get_market_context
    mock_market_context = AsyncMock(return_value={'volatility': 0.2, 'regime': 'NEUTRAL'})
    monkeypatch.setattr('backend.agents.technical.base.TechnicalAgent.get_market_context', mock_market_context)

    # Set up Redis mock instance and return value correctly
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get = AsyncMock(return_value=None)  # Simulate cache miss
    mock_redis_instance.set = AsyncMock()

    # Configure the mock for get_redis_client to return the instance correctly
    # mock_get_redis_arg is the AsyncMock for get_redis_client
    mock_get_redis_arg.return_value = mock_redis_instance

    # Mock tracker instance returned by get_tracker
    # mock_get_tracker_arg is the MagicMock for get_tracker
    mock_tracker_instance = MagicMock()
    mock_tracker_instance.update_agent_status = AsyncMock()
    mock_get_tracker_arg.return_value = mock_tracker_instance

    # Run the agent - pass agent_outputs explicitly
    res = await st_run('TCS', agent_outputs={})

    # Verify mocks were called correctly
    mock_fetch.assert_called_once()
    mock_market_context.assert_called_once()
    mock_get_redis_arg.assert_awaited_once() # Verify the AsyncMock for get_redis_client was awaited
    mock_redis_instance.get.assert_awaited_once()

    # Ensure the result is JSON serializable (this also confirms 'res' is a valid dict)
    import json
    json.dumps(res) # If this fails, the test should fail here.

    # After a cache miss and successful agent execution (implicit by json.dumps not failing),
    # the standard_agent_execution decorator should cache the result.
    mock_redis_instance.set.assert_awaited_once()

    # Verify tracker update was called
    mock_get_tracker_arg.assert_called_once() # Verify the MagicMock for get_tracker was called
    # Ensure update_agent_status is awaited if the agent run was successful or a known non-caching error
    # The decorator calls update_agent_status in most paths.
    mock_tracker_instance.update_agent_status.assert_awaited_once()

    # Verify results
    assert 'verdict' in res
    assert res['verdict'] in ['BUY', 'SELL', 'HOLD', 'NO_DATA', 'ERROR']  # Allow for different outcomes
    assert 'value' in res  # Supertrend value
    assert 'confidence' in res
    assert isinstance(res['confidence'], float)  # Ensure confidence is a float
    assert 0 <= res['confidence'] <= 1  # Confidence should be between 0 and 1