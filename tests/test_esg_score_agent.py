import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import pytest
from backend.agents.esg.esg_score_agent import run as esg_run

@pytest.mark.asyncio
async def test_esg_score_agent(monkeypatch):
    # Stub ESG data
    monkeypatch.setattr('backend.utils.data_provider.fetch_esg_data', lambda symbol: {'score': 75})
    res = await esg_run('ABC')
    assert 'value' in res # Check for the 'value' key which holds the composite score
    assert isinstance(res['value'], (int, float)) # Ensure the score is a number