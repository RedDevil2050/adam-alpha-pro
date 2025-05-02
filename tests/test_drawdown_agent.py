import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import pandas as pd # Import pandas here
from unittest.mock import AsyncMock # Import AsyncMock
from backend.utils.data_provider import fetch_price_series
from backend.agents.risk.drawdown_agent import run

@pytest.fixture(autouse=True)
def mock_price_series(monkeypatch):
    # import pandas as pd # Moved import to top
    dates = pd.date_range(end='2025-04-05', periods=5)
    series = pd.Series([100,120,110,90,95], index=dates)
    # Correct the mock signature: make it async and target where it's used
    mock_fetch = AsyncMock(return_value=series)
    monkeypatch.setattr('backend.agents.risk.drawdown_agent.fetch_price_series', mock_fetch)

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