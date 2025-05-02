import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from backend.utils.data_provider import fetch_price_series
from backend.agents.risk.drawdown_agent import run

@pytest.fixture(autouse=True)
def mock_price_series(monkeypatch):
    import pandas as pd
    dates = pd.date_range(end='2025-04-05', periods=5)
    series = pd.Series([100,120,110,90,95], index=dates)
    # Correct the mock signature: lambda takes only symbol
    monkeypatch.setattr('backend.utils.data_provider.fetch_price_series', lambda sym: series)

@pytest.mark.asyncio
async def test_drawdown_agent():
    result = await run('TEST')
    # Check for error first
    if result.get('error'):
        pytest.fail(f"Agent returned an error: {result['error']}")
    if result['verdict'] != 'NO_DATA':
        # Assertions for successful run
        assert 'details' in result
        assert 'max_drawdown' in result['details'] # Check details dict
        assert isinstance(result['details']['max_drawdown'], float)
        assert 'value' in result # Check value field
        assert isinstance(result['value'], float)
        assert result['details']['max_drawdown'] == result['value']
        assert result['verdict'] in ['LOW_DRAWDOWN', 'MODERATE_DRAWDOWN', 'HIGH_DRAWDOWN']
    else:
        # Assertions for NO_DATA case
        assert 'max_drawdown' not in result.get('details', {})
        assert result.get('value') is None