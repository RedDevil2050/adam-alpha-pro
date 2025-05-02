import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import pytest
from unittest.mock import AsyncMock, patch
from backend.agents.valuation.pfcf_ratio_agent import run as prun

@pytest.mark.asyncio
@patch('backend.agents.decorators.get_redis_client') # Corrected patch target
@patch('backend.agents.valuation.pfcf_ratio_agent.fetch_cash_flow_data') # Patch cash flow fetch
@patch('backend.agents.valuation.pfcf_ratio_agent.fetch_company_info') # Patch company info fetch
async def test_pfcf_ratio_agent(mock_fetch_info, mock_fetch_cf, mock_get_redis):
    # Mock company info (for Market Cap)
    mock_fetch_info.return_value = {
        "MarketCapitalization": "1000000000" # Example Market Cap
    }
    # Mock cash flow data (for OCF and CapEx) - Alpha Vantage like structure
    mock_fetch_cf.return_value = {
        "annualReports": [
            {
                "operatingCashflow": "150000000", # Example OCF
                "capitalExpenditures": "-50000000" # Example CapEx (negative)
            }
            # ... older reports ...
        ]
    }

    # Mock Redis
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get.return_value = None # Cache miss
    mock_redis_instance.set = AsyncMock()

    # Configure the mock for get_redis_client to return the instance correctly
    async def fake_get_redis():
        return mock_redis_instance
    mock_get_redis.side_effect = fake_get_redis

    # Expected calculations:
    # FCF = OCF - abs(CapEx) = 150M - 50M = 100M
    # P/FCF = Market Cap / FCF = 1000M / 100M = 10.0

    res = await prun('ABC') # Pass only symbol, decorator handles agent_outputs

    # Assertions
    assert res['symbol'] == 'ABC'
    assert 'value' in res # 'value' should contain the P/FCF ratio
    assert res['value'] == pytest.approx(10.0)
    assert 'details' in res
    assert 'pfcf_ratio' in res['details']
    assert res['details']['pfcf_ratio'] == pytest.approx(10.0)
    assert res['details']['free_cash_flow'] == pytest.approx(100000000.0)
    assert res['verdict'] == 'LOW_PFCF' # Based on ratio < 15
    assert res.get('error') is None

    # Verify mocks
    mock_fetch_info.assert_awaited_once_with('ABC')
    mock_fetch_cf.assert_awaited_once_with('ABC')
    mock_get_redis.assert_awaited_once() # Verify the patch target was called
    mock_redis_instance.get.assert_awaited_once()
    mock_redis_instance.set.assert_awaited_once()