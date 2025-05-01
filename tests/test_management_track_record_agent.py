import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import pytest
from unittest.mock import AsyncMock
# Corrected import path
from backend.agents.management.management_track_record_agent import run as mgt_run

@pytest.mark.asyncio
async def test_management_track_record_agent(monkeypatch):
    # Mock the fetch_transcript function which the agent now uses
    mock_transcript = "Management expressed strong confidence about future growth."
    monkeypatch.setattr('backend.utils.data_provider.fetch_transcript', AsyncMock(return_value=mock_transcript))
    
    # Mock redis get/set as the agent uses caching
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get.return_value = None # Simulate cache miss
    mock_redis_instance.set.return_value = None
    monkeypatch.setattr('backend.utils.cache_utils.get_redis_client', AsyncMock(return_value=mock_redis_instance))

    # Call run with only the symbol argument
    res = await mgt_run('ABC')
    
    # Assert based on the agent's sentiment analysis logic
    assert 'verdict' in res
    # Based on the mock transcript and VADER score > 0.2
    assert res['verdict'] == 'POSITIVE_CONFIDENCE' 
    assert 'value' in res
    assert isinstance(res['value'], float)
    assert res['value'] > 0.2 # Check the compound score
    
    # Verify cache was checked and set
    mock_redis_instance.get.assert_awaited_once()
    mock_redis_instance.set.assert_awaited_once()