import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import pytest
import pandas as pd
import numpy as np
from backend.agents.valuation.book_to_market_agent import run as bm_run
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_book_to_market_agent(monkeypatch):
    # Mock dependencies - adjust mocks as needed for realistic data
    # Patch fetch_book_value where it's used in the agent module
    monkeypatch.setattr('backend.agents.valuation.book_to_market_agent.fetch_book_value', AsyncMock(return_value=50.0))
    # Mock price point to return a dictionary as expected by the agent
    monkeypatch.setattr('backend.utils.data_provider.fetch_price_point', AsyncMock(return_value={"latestPrice": 100.0}))
    # Mock historical prices to allow percentile calculation
    dates = pd.date_range(end='2025-05-03', periods=100)
    hist_prices = pd.Series(np.random.normal(100, 10, 100), index=dates)
    # Patch fetch_historical_price_series where it's used in the agent module
    monkeypatch.setattr('backend.agents.valuation.book_to_market_agent.fetch_historical_price_series', AsyncMock(return_value=hist_prices))
    # Mock settings if necessary (using defaults here)
    # from backend.config.settings import Settings
    # monkeypatch.setattr('backend.agents.valuation.book_to_market_agent.get_settings', lambda: Settings())

    res = await bm_run('ABC', {})

    # Assertions
    assert res['symbol'] == 'ABC'
    assert 'value' in res # Check for the primary value field
    assert isinstance(res['value'], float)
    assert res['value'] == pytest.approx(0.5) # 50.0 / 100.0
    assert 'details' in res
    assert 'btm_ratio' in res['details'] # Check for btm_ratio in details
    assert res['details']['btm_ratio'] == res['value']
    assert 'verdict' in res
    assert res.get('error') is None