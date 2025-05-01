import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import asyncio
# Import the agent's run function
from backend.agents.valuation.price_to_book_agent import run as ptb_run
# Import the functions the agent actually uses
from backend.utils.data_provider import fetch_company_info, fetch_price_point
from unittest.mock import patch, AsyncMock # Import patch and AsyncMock

@pytest.mark.asyncio
# Patch the functions the agent uses
@patch('backend.agents.valuation.price_to_book_agent.fetch_price_point')
@patch('backend.agents.valuation.price_to_book_agent.fetch_company_info')
async def test_price_to_book_agent(mock_fetch_company_info, mock_fetch_price_point):
    # Mock the return value of fetch_company_info
    mock_fetch_company_info.return_value = {
        "BookValuePerShare": "20.0" # Simulate string value
    }
    # Mock the return value of fetch_price_point
    mock_fetch_price_point.return_value = {
        "price": 30.0 # Simulate float value
    }
    
    # Call the agent's run function
    result = await ptb_run('TEST')
    
    # Assert based on the agent's actual return structure
    expected_pb = 30.0 / 20.0 # 1.5
    assert result['symbol'] == 'TEST'
    # Assert the 'value' key which holds the calculated P/B ratio
    assert result['value'] == pytest.approx(expected_pb)
    # Assert the verdict based on the agent's logic (1.5 is between 1 and 3)
    assert result['verdict'] == 'HOLD' 
    assert 'details' in result
    assert result['details']['price_to_book'] == pytest.approx(expected_pb)
    assert result.get('error') is None

    # Verify the mocks were called
    mock_fetch_company_info.assert_awaited_once_with('TEST')
    mock_fetch_price_point.assert_awaited_once_with('TEST')