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
    monkeypatch.setattr('backend.utils.data_provider.fetch_price_series', lambda sym, period: series)

@pytest.mark.asyncio
async def test_drawdown_agent():
    result = await run('TEST')
    assert 'max_drawdown_pct' in result and isinstance(result['max_drawdown_pct'], float)
    assert result['verdict'] in ['BUY','HOLD','SELL']