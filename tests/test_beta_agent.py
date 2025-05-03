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
        if sym == 'TEST' or sym == market_symbol:
            return series
        raise ValueError(f"Unexpected symbol {sym} in mock_fetch_price_series")

    monkeypatch.setattr('backend.utils.data_provider.fetch_price_series', mock_fetch)

@pytest.mark.asyncio
async def test_beta_agent():
    result = await run('TEST')
    # Assert based on the agent's actual return structure
    assert result['symbol'] == 'TEST'
    assert 'value' in result and isinstance(result['value'], (float, np.floating)) # Beta is in 'value'
    assert 'confidence' in result and isinstance(result['confidence'], float)
    assert 'details' in result
    assert 'beta' in result['details'] # Beta is also in details
    # Assert the correct verdict types
    assert result['verdict'] in ['LOW_RISK', 'MODERATE_RISK', 'HIGH_RISK', 'NO_DATA', 'ERROR'] # Include NO_DATA/ERROR
    assert result.get('error') is None