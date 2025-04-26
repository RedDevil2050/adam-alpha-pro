import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import pytest
from backend.agents.esg.management_track_record_agent import run as mgt_run

@pytest.mark.asyncio
async def test_management_track_record_agent(monkeypatch):
    # Stub management data
    monkeypatch.setattr('backend.utils.data_provider.fetch_management_data', lambda symbol: {'roe': 15})
    res = await mgt_run('ABC', {})
    assert 'management_score' in res
    assert isinstance(res['management_score'], (int, float))