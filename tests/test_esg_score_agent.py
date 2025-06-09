import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import pytest
from unittest.mock import patch, AsyncMock
from backend.agents.esg.esg_score_agent import run as esg_run

@pytest.mark.asyncio
@patch('backend.agents.decorators.get_redis_client', new_callable=AsyncMock)  # Patch decorator's redis client
@patch('backend.agents.esg.esg_score_agent.fetch_esg_data', new_callable=AsyncMock)
async def test_esg_score_agent(mock_fetch_esg, mock_get_redis):
    # Mock ESG data with the correct structure expected by the agent
    mock_fetch_esg.return_value = {
        'environmental': 80,
        'social': 70, 
        'governance': 75
    }
    
    # Mock Redis
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get.return_value = None  # Cache miss
    mock_redis_instance.set = AsyncMock()
    mock_get_redis.return_value = mock_redis_instance
    
    res = await esg_run('ABC')
    assert 'value' in res # Check for the 'value' key which holds the composite score
    assert isinstance(res['value'], (int, float)) # Ensure the score is a number
    
    # Verify the mocks were called
    mock_fetch_esg.assert_awaited_once_with('ABC')
    mock_get_redis.assert_awaited_once()