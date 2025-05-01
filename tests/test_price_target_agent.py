import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import asyncio
from backend.agents.valuation.price_target_agent import run as pt_run
from backend.utils.data_provider import fetch_company_info
from unittest.mock import patch

@pytest.mark.asyncio
@patch('backend.agents.valuation.price_target_agent.fetch_company_info')
async def test_price_target_agent(mock_fetch_company_info):
    mock_fetch_company_info.return_value = {
        "AnalystTargetPrice": "150.50"
    }
    
    result = await pt_run('TEST')
    
    assert result['symbol'] == 'TEST'
    assert result['verdict'] == 'ANALYST_TARGET_PRICE_AVAILABLE'
    assert result['value'] == 150.50
    assert 'details' in result
    assert result['details']['analyst_target_price'] == 150.50
    assert result.get('error') is None

    mock_fetch_company_info.assert_awaited_once_with('TEST')