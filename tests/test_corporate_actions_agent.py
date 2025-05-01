import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest.mock import AsyncMock, patch
from backend.agents.event.corporate_actions_agent import run as ca_run
import datetime

agent_name = "corporate_actions_agent"

@pytest.mark.asyncio
# Patch dependencies (innermost first)
@patch('backend.agents.event.utils.tracker.update') # Assuming tracker is in event.utils
@patch('backend.agents.event.corporate_actions_agent.get_redis_client')
@patch('backend.agents.event.corporate_actions_agent.fetch_corporate_actions')
async def test_corporate_actions_agent_active(
    mock_fetch_actions, 
    mock_get_redis, 
    mock_tracker_update
):
    # --- Mock Configuration ---
    # 1. Mock fetch_corporate_actions to return multiple actions
    mock_actions_data = [
        {"date": "2025-04-15", "type": "Dividend", "details": "$0.50 per share"},
        {"date": "2025-03-01", "type": "Split", "details": "2-for-1"},
        {"date": "2025-01-10", "type": "Bonus", "details": "1:5"},
        # Add more if needed to test different score thresholds
    ]
    mock_fetch_actions.return_value = mock_actions_data
    expected_count = len(mock_actions_data)
    # Expected score = min(3 / 5.0, 1.0) = 0.6
    expected_score = 0.6
    expected_verdict = "ACTIVE" # Since score >= 0.6
    
    # 2. Mock Redis
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get.return_value = None # Cache miss
    mock_redis_instance.set = AsyncMock()
    mock_get_redis.return_value = mock_redis_instance

    # 3. Mock Tracker (already patched)
    mock_tracker_update.return_value = None # Simple mock

    # --- Run Agent ---
    res = await ca_run('TEST_SYMBOL')
    
    # --- Assertions ---
    assert res['symbol'] == 'TEST_SYMBOL'
    assert res['agent_name'] == agent_name
    assert res['verdict'] == expected_verdict
    assert res['confidence'] == pytest.approx(expected_score)
    assert res['value'] == expected_count # Value is the count of actions
    assert res.get('error') is None
    
    # Check details
    assert 'details' in res
    details = res['details']
    assert details['actions_count'] == expected_count
    # Check if recent_actions are included (up to 3)
    assert 'recent_actions' in details
    assert len(details['recent_actions']) == min(expected_count, 3)
    if expected_count > 0:
        assert details['recent_actions'][0] == mock_actions_data[0]

    # --- Verify Mocks ---
    mock_fetch_actions.assert_awaited_once_with('TEST_SYMBOL')
    mock_get_redis.assert_awaited_once()
    mock_redis_instance.get.assert_awaited_once()
    mock_redis_instance.set.assert_awaited_once() # Should cache on success
    mock_tracker_update.assert_called_once_with("event", agent_name, "implemented")
