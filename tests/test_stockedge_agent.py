import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import pytest
from unittest.mock import patch, AsyncMock # Import patch and AsyncMock
from backend.agents.stealth.stockedge_agent import run as se_run, StockEdgeAgent # Import class

@pytest.mark.asyncio
# Patch the _fetch_stealth_data method within the test
@patch.object(StockEdgeAgent, '_fetch_stealth_data', new_callable=AsyncMock)
async def test_stockedge_agent(mock_fetch_data, monkeypatch): # Add mock to args
    # monkeypatch.setattr('backend.utils.data_provider.fetch_price_alpha_vantage', lambda s: 120.0) # Keep if needed, but likely not for unit test

    # --- Mock Configuration ---
    symbol = 'ABC'
    # Define sample data that _fetch_stealth_data would return
    mock_data = {
        "quality_score": 75.0,
        "technicals": {"SMA(20)": "Buy", "RSI(14)": "Neutral"},
        "metrics": {"P/E": "25.0", "Market Cap": "100B"},
        "source": "stockedge",
    }
    mock_fetch_data.return_value = mock_data

    # --- Run Agent ---
    res = await se_run(symbol)

    # --- Assertions ---
    assert 'agent_name' in res
    assert res['agent_name'] == 'stockedge_agent'
    assert 'details' in res
    # Assert based on the mocked data and agent logic
    assert res['details'] == mock_data
    assert 'value' in res
    assert isinstance(res['value'], float)
    # Expected score: (75/100 + 1/2) / 2 = (0.75 + 0.5) / 2 = 0.625
    assert res['value'] == pytest.approx(0.625)
    assert 'verdict' in res
    # Expected verdict for score 0.625 is AVERAGE_QUALITY
    assert res['verdict'] == 'AVERAGE_QUALITY'
    assert res.get('error') is None

    # --- Verify Mocks ---
    mock_fetch_data.assert_awaited_once_with(symbol)