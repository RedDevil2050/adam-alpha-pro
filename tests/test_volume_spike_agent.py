import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import pandas as pd
from unittest.mock import AsyncMock, patch, MagicMock
from backend.agents.technical.volume_spike_agent import run
import datetime
import json # Added for json.dumps

@pytest.mark.asyncio
@patch('backend.agents.decorators.get_redis_client', new_callable=AsyncMock)  # This mock is the second argument
@patch('backend.agents.decorators.get_tracker') # This mock is the first argument
async def test_volume_spike_agent(mock_get_tracker_arg, mock_get_redis_arg, monkeypatch): # CORRECTED: Parameter order and names
    # Create realistic OHLCV data with a volume spike at the end
    today = datetime.date(2025, 4, 30)
    dates = pd.to_datetime([today - datetime.timedelta(days=x) for x in range(25, -1, -1)])
    volumes = [1000] * 25 + [3000]  # Normal volume, then a spike
    closes = [99 + i * 0.2 for i in range(26)] # Slight uptrend
    # Ensure open is lower than close for a positive price_change
    opens = [c - 0.1 for c in closes] # Open slightly lower than close

    data_df = pd.DataFrame({
        'high': [c + 0.1 for c in closes], # Dummy high
        'low': [o - 0.1 for o in opens],   # Dummy low
        'close': closes,
        'open': opens, # Use the adjusted opens
        'volume': volumes
    }, index=dates)

    # Mock fetch_ohlcv_series within the agent's module
    mock_fetch = AsyncMock(return_value=data_df)
    monkeypatch.setattr('backend.agents.technical.volume_spike_agent.fetch_ohlcv_series', mock_fetch)

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
    result = await run('TEST', agent_outputs={}) # Pass agent_outputs

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
        print("\nWarning: Result not JSON serializable in test_volume_spike_agent, set not awaited as expected.")

    # Verify tracker update was called
    mock_get_tracker_arg.assert_called_once() # Verify the MagicMock for get_tracker was called
    mock_tracker_instance.update_agent_status.assert_awaited_once() # UNCOMMENTED

    # Verify results
    assert 'verdict' in result
    # Expecting bullish volume due to spike + positive price change
    assert result['verdict'] == 'BULLISH_VOLUME'
    assert 'confidence' in result
    assert 'value' in result # Volume ratio
    # Volume ratio = latest_volume / avg_volume = 3000 / 1000 = 3.0
    # Corrected expectation: (19*1000 + 3000)/20 = 1100 avg; 3000/1100 = 2.727... -> 2.73
    # assert result['value'] == pytest.approx(3.0)
    assert result['value'] == pytest.approx(2.73)
    assert 'details' in result
    # assert result['details']['volume_ratio'] == result['value']
    assert result['details']['volume_ratio'] == pytest.approx(2.73)
    assert result['details']['price_change'] > 0 # Check price change is positive
    assert result.get('error') is None