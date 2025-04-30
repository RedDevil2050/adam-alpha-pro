import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import asyncio
from backend.agents.technical.volume_spike_agent import run
from backend.utils.data_provider import fetch_alpha_vantage

@pytest.fixture(autouse=True)
def mock_data(monkeypatch):
    async def fake_alpha(endpoint, params):
        # Create 60 days of dummy OHLCV
        import pandas as pd
        data = {}
        for i in range(1, 61):
            date = f'2025-04-{i:02d}'
            data[date] = {
                '1. open': '100', '2. high': '110', '3. low': '90', '4. close': str(100 + i), '5. adjusted close': str(100 + i),
                '5. volume': '1000'
            }
        if params.get('function') == 'ATR':
            return {'Technical Analysis: ATR': {date: '2.5' for date in data}}
        if params.get('function') == 'ADX':
            return {'Technical Analysis: ADX': {date: '30' for date in data}}
        return {'Time Series (Daily)': data}

@pytest.mark.asyncio
async def test_volume_spike_agent():
    result = await run('TEST', {})
    assert 'spike_ratio' in result
    assert 'verdict' in result
    assert 'confidence' in result
    assert isinstance(result['confidence'], float)