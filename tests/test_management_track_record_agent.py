import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest.mock import AsyncMock, patch
# Corrected import path
from backend.agents.management.management_track_record_agent import run as mgt_run

agent_name = "management_track_record_agent"

@pytest.mark.asyncio
# Patch dependencies using decorators (innermost first)
@patch('backend.agents.base.get_redis_client', new_callable=AsyncMock) # For AgentBase
@patch('backend.agents.management.management_track_record_agent.get_redis_client', new_callable=AsyncMock) # For decorator/agent-specific
@patch('backend.agents.technical.utils.tracker.update') # Correct path based on agent import
# Correct the patch target to the source module
@patch('backend.utils.data_provider.fetch_transcript') 
# Optionally patch the analyzer for full control, but mocking transcript is often sufficient
# @patch('backend.agents.management.management_track_record_agent.SentimentIntensityAnalyzer')
async def test_management_track_record_agent(
    mock_fetch_transcript, 
    mock_tracker_update, # Order adjusted due to new patches
    mock_agent_get_redis, # Corresponds to management_track_record_agent.get_redis_client
    mock_base_get_redis,  # Corresponds to base.get_redis_client
    # mock_analyzer # Add if patching analyzer
):
    # --- Mock Configuration ---
    # 1. Mock fetch_transcript
    mock_transcript = "Management expressed strong confidence about future growth."
    mock_fetch_transcript.return_value = mock_transcript
    
    # 2. Mock Redis
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get = AsyncMock(return_value=None) # Simulate cache miss
    mock_redis_instance.set = AsyncMock()
    mock_agent_get_redis.return_value = mock_redis_instance
    mock_base_get_redis.return_value = mock_redis_instance

    # 3. Mock Tracker (already patched)
    # mock_tracker_update.return_value = None # Simple mock - this is already an arg

    # --- Run Agent ---
    res = await mgt_run('ABC')
    
    # --- Assertions ---
    # Assert based on the agent's sentiment analysis logic and the positive mock transcript
    assert res['symbol'] == 'ABC'
    assert res['agent_name'] == agent_name
    assert 'verdict' in res
    # VADER score for the mock transcript is likely > 0.2
    assert res['verdict'] == 'POSITIVE_CONFIDENCE' 
    assert 'value' in res # Raw compound score
    assert isinstance(res['value'], float)
    assert res['value'] > 0.2 # Check the compound score threshold
    assert 'confidence' in res # Absolute value of compound score
    assert res['confidence'] == pytest.approx(abs(res['value']))
    assert res.get('error') is None, f"Agent returned error: {res.get('error')}"
    
    # --- Verify Mocks ---
    mock_fetch_transcript.assert_awaited_once_with('ABC')
    mock_agent_get_redis.assert_awaited_once()
    assert mock_redis_instance.get.await_count >= 1 # Called by decorator and/or base
    if res.get('verdict') not in ['NO_DATA', 'ERROR', None]:
        assert mock_redis_instance.set.await_count >= 1 # Called by decorator and/or base
    mock_tracker_update.assert_called_once_with("management", agent_name, "implemented")