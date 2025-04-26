import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import asyncio
import importlib.util
import os

# Dynamically load agent module
agent_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend/agents/forecast/earnings_forecast_agent.py'))
spec = importlib.util.spec_from_file_location('ef_agent', agent_path)
ef_agent = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ef_agent)

# Stub data provider directly on module
async def fake_earnings(symbol):
    return {'earnings': [{'estimate': 2.0, 'actual': 1.5}]}

@pytest.mark.asyncio
async def test_earnings_forecast_agent(monkeypatch):
    # Patch the fetch_iex_earnings used within the module
    ef_agent.fetch_iex_earnings = fake_earnings
    result = await ef_agent.run('TEST', {})
    assert result['symbol'] == 'TEST'
    assert 'estimate' in result and 'actual' in result
    assert result['verdict'] in ['BUY','HOLD','SELL']