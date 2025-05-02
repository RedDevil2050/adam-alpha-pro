import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import pytest
from unittest.mock import AsyncMock # Import AsyncMock
from backend.agents.automation.alert_engine_agent import run as alert_run

@pytest.mark.asyncio
async def test_alert_engine_agent(monkeypatch):
    monkeypatch.setattr('backend.utils.data_provider.fetch_alerts', lambda: [])
    # Mock fetch_price_series to return dummy data
    monkeypatch.setattr('backend.utils.data_provider.fetch_price_series', AsyncMock(return_value=pd.Series([100.0, 101.0])))
    res = await alert_run('ABC', {})
    assert isinstance(res, dict)
    # Add assertion to check for specific keys or verdict if applicable
    assert 'verdict' in res # Example assertion