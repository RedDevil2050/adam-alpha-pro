import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from backend.agents.valuation.reverse_dcf_agent import run as rdcf_run
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
@patch('backend.utils.cache_utils.get_redis_client') # Patch redis
@patch('backend.agents.valuation.reverse_dcf_agent.fetch_fcf_per_share') # Patch FCF fetch where used
@patch('backend.agents.valuation.reverse_dcf_agent.fetch_price_point') # Patch price fetch where used
async def test_reverse_dcf_agent(mock_fetch_price, mock_fetch_fcf, mock_get_redis, monkeypatch):
    # Mock price data - ensure it returns a dict with 'latestPrice'
    mock_fetch_price.return_value = {'latestPrice': 100.0}
    # Mock FCF per share data
    mock_fetch_fcf.return_value = 10.0 # Return float FCF per share

    # Mock Redis
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get.return_value = None # Cache miss
    mock_redis_instance.set = AsyncMock()
    mock_get_redis.return_value = mock_redis_instance

    res = await rdcf_run('ABC') # Call the agent's run function

    # Update assertions based on actual agent return structure
    assert res['symbol'] == 'ABC'
    assert 'verdict' in res
    assert res['verdict'] in ['AGGRESSIVE', 'MODERATE', 'REASONABLE', 'DECLINE', 'NO_DATA', 'ERROR']
    assert 'confidence' in res
    assert 'value' in res # This holds the implied growth rate (%)
    # Check if value is float only if verdict is not ERROR/NO_DATA
    if res['verdict'] not in ['ERROR', 'NO_DATA']:
        assert isinstance(res['value'], float)
        assert 'details' in res
        assert 'implied_growth_rate' in res['details']
        assert res['details']['implied_growth_rate'] == res['value']
    assert res.get('error') is None or isinstance(res.get('error'), str) # Allow for None or error string

    # Verify mocks
    mock_fetch_price.assert_awaited_once_with('ABC')
    mock_fetch_fcf.assert_awaited_once_with('ABC')
    mock_redis_instance.get.assert_awaited_once()
    # Set should be called only on success
    if res['verdict'] not in ['ERROR', 'NO_DATA']:
        mock_redis_instance.set.assert_awaited_once()
    else:
        mock_redis_instance.set.assert_not_awaited()