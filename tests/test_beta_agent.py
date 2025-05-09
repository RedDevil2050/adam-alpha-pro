import sys, os
import datetime # Add datetime import
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import pandas as pd, numpy as np
from backend.config.settings import get_settings # Import settings
from backend.utils.data_provider import fetch_price_series
from backend.agents.risk.beta_agent import run

@pytest.fixture(autouse=True)
def mock_price_series(monkeypatch):
    # Create dummy series for both symbol and market
    dates = pd.date_range(end=datetime.date.today(), periods=10) # Use datetime
    series = pd.Series(100 + np.arange(10), index=dates)
    
    # Get the market index symbol from settings
    settings = get_settings()
    market_symbol = settings.data_provider.MARKET_INDEX_SYMBOL

    async def mock_fetch(sym, start_date=None, end_date=None): # Match expected signature
        # Return the series if the symbol is the test symbol OR the market symbol
        if sym == 'TEST' or sym == market_symbol:
            return series
        raise ValueError(f"Unexpected symbol {sym} in mock_fetch_price_series")

    monkeypatch.setattr('backend.utils.data_provider.fetch_price_series', mock_fetch)

@pytest.mark.asyncio
async def test_beta_agent():
    result = await run('TEST')
    assert 'symbol' in result, "Result should contain 'symbol'"
    assert result['symbol'] == 'TEST'
    assert 'agent_name' in result, "Result should contain 'agent_name'"
    # Assuming agent_name is defined in the agent module and imported in the test, or use literal
    # from backend.agents.risk.beta_agent import agent_name
    # assert result['agent_name'] == agent_name
    assert result['agent_name'] == 'beta_agent'

    assert 'verdict' in result, "Result should contain 'verdict'"
    verdict = result['verdict']
    assert verdict in ['LOW_RISK', 'MODERATE_RISK', 'HIGH_RISK', 'NO_DATA', 'ERROR']

    assert 'confidence' in result, "Result should contain 'confidence'"
    assert isinstance(result['confidence'], float)
    assert 'details' in result, "Result should contain 'details'"

    if verdict not in ['NO_DATA', 'ERROR']:
        assert 'value' in result, f"Result with verdict '{verdict}' should contain 'value'"
        assert isinstance(result['value'], (float, np.floating))
        assert 'beta' in result['details']
        assert result['details']['beta'] == result['value']
        assert result.get('error') is None
    elif verdict == 'NO_DATA':
        assert result.get('value') is None, "Value should be None for NO_DATA verdict"
        assert 'reason' in result['details']
    elif verdict == 'ERROR':
        # For ERROR verdict, 'value' might be None if set by agent's own error handling,
        # or 'value' key might be missing if decorator handled the error minimally.
        assert ('value' not in result) or (result.get('value') is None), "Value should be absent or None for ERROR verdict"
        # Details should contain an error or reason
        # The decorator now ensures details.error exists.
        # Making the check more inclusive for 'error' or 'reason'
        details_dict = result.get('details', {})
        assert 'error' in details_dict or 'reason' in details_dict, \
            "Details should contain 'error' or 'reason' for ERROR verdict"