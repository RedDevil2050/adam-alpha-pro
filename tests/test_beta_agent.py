import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from backend.utils.data_provider import fetch_price_series
from backend.agents.risk.beta_agent import run

@pytest.fixture(autouse=True)
def mock_price_series(monkeypatch):
    # Create dummy series for both symbol and market
    import pandas as pd, numpy as np
    dates = pd.date_range(end='2025-04-23', periods=10)
    series = pd.Series(100 + np.arange(10), index=dates)
    monkeypatch.setattr('backend.utils.data_provider.fetch_price_series', lambda sym, period: series)

@pytest.mark.asyncio
async def test_beta_agent():
    result = await run('TEST')
    # Assert based on the agent's actual return structure
    assert result['symbol'] == 'TEST'
    assert 'value' in result and isinstance(result['value'], float) # Beta is in 'value'
    assert 'confidence' in result and isinstance(result['confidence'], float)
    assert 'details' in result
    assert 'beta' in result['details'] # Beta is also in details
    # Assert the correct verdict types
    assert result['verdict'] in ['LOW_RISK', 'MODERATE_RISK', 'HIGH_RISK'] 
    assert result.get('error') is None