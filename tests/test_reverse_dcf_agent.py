import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from backend.agents.valuation.reverse_dcf_agent import run as rdcf_run
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_reverse_dcf_agent(monkeypatch):
    # Stub price, cash flows, and discount rate
    # Assuming fetch_price_point is the correct function now
    monkeypatch.setattr('backend.utils.data_provider.fetch_price_point', AsyncMock(return_value={'latestPrice': 100.0})) # Use latestPrice
    # Mock the correct data provider function and return value
    monkeypatch.setattr(
        'backend.utils.data_provider.fetch_fcf_per_share', # Correct function
        AsyncMock(return_value=10.0) # Return float FCF per share
    )
    # Remove unnecessary mocks if not used by reverse_dcf_agent
    # monkeypatch.setattr('backend.utils.data_provider.fetch_wacc', AsyncMock(return_value=0.1))
    # monkeypatch.setattr('backend.utils.data_provider.fetch_company_info', AsyncMock(return_value={'SharesOutstanding': '1000000'}))

    res = await rdcf_run('ABC') # No need for empty dict if default is None

    # Update assertions based on actual agent return structure
    assert 'verdict' in res
    assert 'confidence' in res
    assert 'value' in res # This holds the implied growth rate
    assert isinstance(res['value'], float)
    assert 'details' in res
    assert 'implied_growth_rate' in res['details']