import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from backend.agents.market_regime_agent import run as mr_run

@pytest.mark.asyncio
async def test_market_regime_agent(monkeypatch):
    # Stub market index returns increasing trend - corrected function name
    monkeypatch.setattr('backend.utils.data_provider.fetch_price_series', lambda symbol: [100, 105, 110, 115])
    res = await mr_run('ABC', {})
    assert 'regime' in res
    assert res['regime'] in ['bullish', 'bearish', 'neutral']