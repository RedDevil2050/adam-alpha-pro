import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import pytest
from unittest.mock import AsyncMock # Import AsyncMock
from backend.agents.valuation.intrinsic_composite_agent import run as ic_run

@pytest.mark.asyncio
async def test_intrinsic_composite_agent(monkeypatch):
    # Stub underlying valuations
    stub = {
        'dcf_agent': {'npv': 200.0}, 
        'pe_ratio_agent': {'pe_ratio': 20.0}
        # Add other expected agent results if needed by the composite agent
    }
    # Correct the target and use AsyncMock, assuming run_full_cycle is called
    # The mock should simulate returning results from dependency agents
    monkeypatch.setattr('backend.orchestrator.run_full_cycle', AsyncMock(return_value=stub))
    
    # Pass the stub as agent_outputs if the agent expects pre-run results
    # Or pass {} if it calls run_full_cycle internally
    res = await ic_run('ABC', agent_outputs={}) # Assuming internal call based on mock target
    
    assert 'intrinsic_value' in res
    assert isinstance(res['intrinsic_value'], float)