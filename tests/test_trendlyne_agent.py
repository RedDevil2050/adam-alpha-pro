import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import pytest
from unittest.mock import patch, AsyncMock
from backend.agents.stealth.trendlyne_agent import run as tr_run, TrendlyneAgent

@pytest.mark.asyncio
@patch.object(TrendlyneAgent, '_fetch_stealth_data', new_callable=AsyncMock)
async def test_trendlyne_agent(mock_fetch_data, monkeypatch):
    symbol = 'ABC'
    mock_data = {
        "price": 150.0,
        "technicals": {"SMA(50)": "Above", "MACD(12,26)": "Bullish Crossover"},
        "signals": ["Buy Signal 1", "Strong Buy Signal 2", "Neutral Signal"],
        "source": "trendlyne",
    }
    mock_fetch_data.return_value = mock_data

    res = await tr_run(symbol)

    assert 'symbol' in res
    assert res['symbol'] == symbol
    assert 'agent_name' in res
    assert res['agent_name'] == 'trendlyne_agent'
    assert 'details' in res
    assert res['details'] == mock_data
    assert 'value' in res
    assert isinstance(res['value'], float)
    assert res['value'] == pytest.approx(2/3)
    assert 'verdict' in res
    assert res['verdict'] == 'MIXED_SIGNALS'
    assert 'confidence' in res
    assert isinstance(res['confidence'], float)
    assert res['confidence'] == pytest.approx(0.6)
    assert res.get('error') is None

    mock_fetch_data.assert_awaited_once_with(symbol)