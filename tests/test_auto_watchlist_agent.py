import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest.mock import AsyncMock, patch
import pandas as pd
from backend.agents.automation.auto_watchlist_agent import run as aw_run

@pytest.mark.asyncio
# Patch fetch_price_series in the agent's namespace
@patch('backend.agents.automation.auto_watchlist_agent.fetch_price_series', new_callable=AsyncMock)
async def test_auto_watchlist_agent(mock_fetch_price_series, monkeypatch):
    # monkeypatch.setattr('backend.utils.data_provider.fetch_watchlist', lambda: []) # This mock seems unrelated to the failure
    mock_fetch_price_series.return_value = pd.Series([100.0, 101.0])
    res = await aw_run('ABC', {})
    assert isinstance(res, dict)
    assert 'verdict' in res
    assert res.get('error') is None # Check that no error was reported by the agent
    # Add more specific assertions based on expected behavior with mocked prices
    assert res['details']['signals'] == ["Positive Momentum"]
    assert res['verdict'] == "WATCH"