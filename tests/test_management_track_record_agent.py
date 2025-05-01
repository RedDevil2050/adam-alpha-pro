import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import pytest
from unittest.mock import AsyncMock
# Corrected import path again
from backend.agents.management.management_track_record_agent import run as mgt_run

@pytest.mark.asyncio
async def test_management_track_record_agent(monkeypatch):
    # Stub management data - corrected function name
    monkeypatch.setattr('backend.utils.data_provider.fetch_management_info', AsyncMock(return_value={'roe': 15}))
    # Call run with only the symbol argument
    res = await mgt_run('ABC')
    assert 'management_quality' in res
    assert res['management_quality'] == 'GOOD' # Based on logic for ROE > 10