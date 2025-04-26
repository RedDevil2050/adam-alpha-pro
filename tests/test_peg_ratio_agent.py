import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import asyncio
from backend.agents.valuation.peg_ratio_agent import run
# We will supply agent_outputs to include a prior pe_ratio
@pytest.mark.asyncio
async def test_peg_ratio_agent(monkeypatch):
    agent_outputs = {'TEST': {'pe_ratio_agent': {'pe_ratio': 10.0}}}
    result = await run('TEST', agent_outputs)
    assert result['symbol'] == 'TEST'
    assert 'peg_ratio' in result
    assert result['verdict'] in ['BUY','HOLD','SELL']