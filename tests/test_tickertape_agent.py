import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import pytest
from unittest.mock import patch, AsyncMock # Import patch and AsyncMock
from backend.agents.stealth.tickertape_agent import run as tt_run, TickertapeAgent # Import class

# Remove the fixture mocking fetch_price_alpha_vantage as it's not needed for unit test
# @pytest.fixture(autouse=True)
# def mock_fetch_price_alpha_vantage(monkeypatch):
#     async def mock_fetch(symbol):
#         return {"price": 200.0}
#     monkeypatch.setattr('backend.utils.data_provider.fetch_price_alpha_vantage', mock_fetch)


@pytest.mark.asyncio
# Patch the _fetch_stealth_data method
@patch.object(TickertapeAgent, '_fetch_stealth_data', new_callable=AsyncMock)
async def test_tickertape_agent(mock_fetch_data): # Add mock to args
    # --- Mock Configuration ---
    symbol = 'ABC'
    # Define sample data that _fetch_stealth_data would return
    mock_data = {
        "ratios": {"P/E": "30.0", "P/B": "3.0"},
        "recommendations": ["Buy", "Buy", "Hold", "Buy", "Sell"], # 3 Buy out of 5
        "source": "tickertape",
    }
    mock_fetch_data.return_value = mock_data

    # --- Run Agent ---
    res = await tt_run(symbol)

    # --- Assertions ---
    assert 'symbol' in res
    assert res['symbol'] == symbol
    assert 'agent_name' in res
    assert res['agent_name'] == 'tickertape_agent'
    assert 'details' in res
    assert res['details'] == mock_data
    assert 'value' in res
    assert isinstance(res['value'], float)
    # Expected score: 3 buys / 5 recs = 0.6
    assert res['value'] == pytest.approx(0.6)
    assert 'verdict' in res
    # Expected verdict for score 0.6 is MIXED_CONSENSUS
    assert res['verdict'] == 'MIXED_CONSENSUS'
    assert 'confidence' in res
    assert isinstance(res['confidence'], float)
    # Expected confidence: score * 0.85 = 0.6 * 0.85 = 0.51
    assert res['confidence'] == pytest.approx(0.51)
    assert res.get('error') is None

    # --- Verify Mocks ---
    mock_fetch_data.assert_awaited_once_with(symbol)