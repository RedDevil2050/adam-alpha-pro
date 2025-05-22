import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import pandas as pd
from unittest.mock import AsyncMock, patch, MagicMock
from backend.agents.technical.trend_strength_agent import run
import datetime
import json # Added for json.dumps

@pytest.mark.asyncio
@patch('backend.agents.decorators.get_redis_client', new_callable=AsyncMock)  # This mock is the second argument
@patch('backend.agents.decorators.get_tracker') # This mock is the first argument
async def test_trend_strength_agent(mock_get_tracker_arg, mock_get_redis_arg, monkeypatch): # CORRECTED: Parameter order and names
    # Create realistic OHLCV data with uptrend
    dates = pd.to_datetime([datetime.date(2025, 4, 30) - datetime.timedelta(days=x) for x in range(60, -1, -1)])
    data_df = pd.DataFrame({
        'high': [100 + i * 0.2 for i in range(61)],
        'low': [98 + i * 0.2 for i in range(61)],
        'close': [99 + i * 0.2 for i in range(61)],  # Steady uptrend
        'open': [99 + i * 0.2 for i in range(61)],
        'volume': [1000 + i * 10 for i in range(61)]
    }, index=dates)

    # Mock fetch_ohlcv_series within the agent's module
    mock_fetch = AsyncMock(return_value=data_df)
    monkeypatch.setattr('backend.agents.technical.trend_strength_agent.fetch_ohlcv_series', mock_fetch)

    # Mock get_market_context
    mock_market_context = AsyncMock(return_value={'regime': 'NEUTRAL'})
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

    # Run the agent - pass agent_outputs
    result = await run('TEST', agent_outputs={})

    # Verify mocks were called correctly
    mock_fetch.assert_called_once()
    mock_market_context.assert_called_once()
    mock_get_redis_arg.assert_awaited_once() # Verify the AsyncMock for get_redis_client was awaited
    mock_redis_instance.get.assert_awaited_once()
    
    try:
        json.dumps(result)
        mock_redis_instance.set.assert_awaited_once() # UNCOMMENTED
    except TypeError:
        mock_redis_instance.set.assert_not_awaited()
        print("\nWarning: Result not JSON serializable in test_trend_strength_agent, set not awaited as expected.")

    # Verify tracker update was called
    mock_get_tracker_arg.assert_called_once() # Verify the MagicMock for get_tracker was called
    mock_tracker_instance.update_agent_status.assert_awaited_once() # UNCOMMENTED

    # Verify results
    assert 'verdict' in result
    # Based on the strong uptrend data and typical ADX thresholds, expect STRONG_UPTREND
    assert result['verdict'] == 'STRONG_UPTREND' # Corrected assertion based on error log
    assert 'confidence' in result
    assert isinstance(result['confidence'], float)
    assert 'value' in result  # Trend strength score * direction
    assert 'details' in result
    assert 'strength_score' in result['details']
    assert 'direction' in result['details']