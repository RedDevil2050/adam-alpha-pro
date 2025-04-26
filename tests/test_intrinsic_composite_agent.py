import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import pytest
from backend.agents.valuation.intrinsic_composite_agent import run as ic_run

@pytest.mark.asyncio
async def test_intrinsic_composite_agent(monkeypatch):
    # Stub underlying valuations
    stub = {'npv': 200.0, 'pe_ratio': 20.0, 'dcf':200.0}
    monkeypatch.setattr('backend.orchestrator.run_orchestration', lambda s: stub)
    res = await ic_run('ABC', {})
    assert 'intrinsic_value' in res
    assert isinstance(res['intrinsic_value'], float)