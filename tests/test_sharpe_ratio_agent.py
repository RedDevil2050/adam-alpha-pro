import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from backend.utils.data_provider import fetch_price_series
from backend.agents.risk.sharpe_ratio_agent import run

@pytest.fixture(autouse=True)
def mock_price_series(monkeypatch):
    import pandas as pd, numpy as np
    dates = pd.date_range(end='2025-04-23', periods=10)
    series = pd.Series(100 + np.sin(np.linspace(0,3,10)), index=dates)
    monkeypatch.setattr('backend.utils.data_provider.fetch_price_series', lambda sym, period: series)

@pytest.mark.asyncio
async def test_sharpe_ratio_agent():
    result = await run('TEST', {})
    assert 'sharpe_ratio' in result and isinstance(result['sharpe_ratio'], float)
    assert result['verdict'] in ['BUY','HOLD','SELL']