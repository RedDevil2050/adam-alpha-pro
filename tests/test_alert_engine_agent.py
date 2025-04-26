import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import pytest
from backend.agents.automation.alert_engine_agent import run as alert_run

@pytest.mark.asyncio
async def test_alert_engine_agent(monkeypatch):
    monkeypatch.setattr('backend.utils.data_provider.fetch_alerts', lambda: [])
    res = await alert_run('ABC', {})
    assert isinstance(res, dict)