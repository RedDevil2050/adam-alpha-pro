import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest.mock import AsyncMock, patch # Import patch
import pandas as pd
from backend.agents.automation.auto_watchlist_agent import run as aw_run

@pytest.mark.asyncio
@patch('backend.utils.data_provider.fetch_price_series', new_callable=AsyncMock)
async def test_auto_watchlist_agent(mock_fetch_price_series, monkeypatch): # mock_fetch_price_series is now an arg
    monkeypatch.setattr('backend.utils.data_provider.fetch_watchlist', lambda: [])
    mock_fetch_price_series.return_value = pd.Series([100.0, 101.0])
    res = await aw_run('ABC', {})
    assert isinstance(res, dict)
    # Add assertion to check for specific keys or verdict if applicable
    assert 'verdict' in res # Example assertion