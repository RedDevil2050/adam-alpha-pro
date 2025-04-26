import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import asyncio
import importlib.util
import os

# Dynamically load agent module
agent_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend/agents/forecast/price_forecast_agent.py'))
spec = importlib.util.spec_from_file_location('pf_agent', agent_path)
pf_agent = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pf_agent)

# Stub data provider
from backend.utils.data_provider import fetch_alpha_vantage
async def fake_alpha(endpoint, params):
    import pandas as pd
    data = {}
    for i in range(1, 101):
        data[f'2025-04-{i:02d}'] = {'4. close': str(100 + i)}
    return data and {'Time Series (Daily)': data}

@pytest.mark.asyncio
async def test_price_forecast_agent(monkeypatch):
    monkeypatch.setattr('backend.utils.data_provider.fetch_alpha_vantage', fake_alpha)
    result = await pf_agent.run('TEST', {})
    assert 'forecast_change_pct' in result
    assert result['verdict'] in ['BUY','HOLD','SELL']