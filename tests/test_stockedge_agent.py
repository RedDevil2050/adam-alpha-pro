import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import pytest
from backend.agents.stealth.stockedge_agent import run as se_run

@pytest.mark.asyncio
async def test_stockedge_agent(monkeypatch):
    monkeypatch.setattr('backend.utils.data_provider.fetch_price_alpha_vantage', lambda s: 120.0)
    res = await se_run('ABC')
    assert 'agent_name' in res
    assert res['agent_name'] == 'stockedge_agent'
    assert 'details' in res
    assert 'quality_score' in res['details']
    assert 'metrics' in res['details']
    assert 'value' in res
    assert isinstance(res['value'], float)
    assert 'verdict' in res
    assert res.get('error') is None