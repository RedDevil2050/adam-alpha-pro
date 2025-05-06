import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import asyncio
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock # Added MagicMock

# Import the run function from the agent
from backend.agents.valuation.ev_ebitda_agent import run

# Mock the settings specifically for this agent's test
# from backend.config.settings import Settings, AgentSettings, EvEbitdaAgentSettings # No longer needed directly

@pytest.mark.asyncio
async def test_ev_ebitda_agent_comprehensive(monkeypatch):
    # --- Mock Settings ---
    mock_ev_settings = MagicMock()
    mock_ev_settings.HISTORICAL_YEARS = 1 # Use 1 year for simpler mock data
    mock_ev_settings.PERCENTILE_UNDERVALUED = 25.0
    mock_ev_settings.PERCENTILE_OVERVALUED = 75.0

    mock_agent_settings = MagicMock()
    mock_agent_settings.ev_ebitda = mock_ev_settings

    mock_settings_instance = MagicMock()
    mock_settings_instance.agent_settings = mock_agent_settings

    # Patch get_settings used within the agent
    monkeypatch.setattr('backend.agents.valuation.ev_ebitda_agent.get_settings', MagicMock(return_value=mock_settings_instance))

    # --- Mock Data Provider Functions ---
    # Mock current EV and EBITDA
    mock_fetch_latest_ev = AsyncMock(return_value=2000.0)
    mock_fetch_latest_ebitda = AsyncMock(return_value=100.0)

    # Mock historical EV and EBITDA
    # Create a simple date range for 1 year
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    date_rng = pd.date_range(start=start_date, end=end_date, freq='B') # Business days

    # Mock historical EV series (e.g., constant for simplicity)
    historical_ev_data = [1900.0 + i for i in range(len(date_rng))]
    mock_historical_ev_series = pd.Series(historical_ev_data, index=date_rng)
    mock_fetch_historical_ev = AsyncMock(return_value=mock_historical_ev_series)

    # Mock historical EBITDA series (e.g., slightly increasing)
    historical_ebitda_data = [90.0 + (i * 0.1) for i in range(len(date_rng))]
    mock_historical_ebitda_series = pd.Series(historical_ebitda_data, index=date_rng)
    mock_fetch_historical_ebitda = AsyncMock(return_value=mock_historical_ebitda_series)

    # Patch the data provider functions within the agent's module
    monkeypatch.setattr('backend.agents.valuation.ev_ebitda_agent.fetch_latest_ev', mock_fetch_latest_ev)
    monkeypatch.setattr('backend.agents.valuation.ev_ebitda_agent.fetch_latest_ebitda', mock_fetch_latest_ebitda)
    monkeypatch.setattr('backend.agents.valuation.ev_ebitda_agent.fetch_historical_ev', mock_fetch_historical_ev)
    monkeypatch.setattr('backend.agents.valuation.ev_ebitda_agent.fetch_historical_ebitda', mock_fetch_historical_ebitda)

    # --- Mock Redis for Decorator ---
    mock_redis_client = AsyncMock()
    mock_redis_client.get = AsyncMock(return_value=None)  # Simulate cache miss
    mock_redis_client.set = AsyncMock()
    monkeypatch.setattr('backend.agents.decorators.get_redis_client', AsyncMock(return_value=mock_redis_client))
    
    # --- Mock Tracker for Decorator ---
    mock_tracker_instance = AsyncMock()
    mock_tracker_instance.update_agent_status = AsyncMock()
    monkeypatch.setattr('backend.agents.decorators.get_tracker', MagicMock(return_value=mock_tracker_instance))


    # --- Run the Agent ---
    symbol = "TEST_EV_EBITDA"
    result = await run(symbol)

    # --- Assertions ---
    assert result is not None
    assert result['symbol'] == symbol
    assert result['agent_name'] == "ev_ebitda_agent"

    # Current EV/EBITDA = 2000 / 100 = 20.0
    assert 'value' in result
    assert result['value'] == pytest.approx(20.0)

    assert 'verdict' in result
    # Based on mock data, current EV/EBITDA is 20.
    # Historical will be around 1900/90 ~ 21 down to (1900+260)/(90+26) ~ 18.6
    # A value of 20 might fall into FAIRLY_VALUED_REL_HIST depending on exact percentile.
    # For this test, let's assume it's fairly valued. More precise mocking would be needed for specific percentile checks.
    # We'll check that it's not an error or no_data state.
    assert result['verdict'] not in ["ERROR", "NO_DATA", "NEGATIVE_OR_ZERO", "NO_HISTORICAL_CONTEXT"]


    assert 'confidence' in result
    assert 0.0 <= result['confidence'] <= 1.0

    assert 'details' in result
    details = result['details']
    assert details['current_ev_ebitda_ratio'] == pytest.approx(20.0)
    assert details['current_ev'] == 2000.0
    assert details['current_ebitda'] == 100.0
    assert 'historical_mean_ev_ebitda' in details
    assert 'historical_std_dev_ev_ebitda' in details
    assert 'percentile_rank' in details
    assert 'z_score' in details
    assert details['data_source'] == "calculated_fundamental + historical_ev_ebitda"
    assert details['config_used']['historical_years'] == 1
    assert details['config_used']['percentile_undervalued'] == 25.0
    assert details['config_used']['percentile_overvalued'] == 75.0

    # Check that fetch functions were called
    mock_fetch_latest_ev.assert_called_once_with(symbol)
    mock_fetch_latest_ebitda.assert_called_once_with(symbol)
    mock_fetch_historical_ev.assert_called_once()
    mock_fetch_historical_ebitda.assert_called_once()

    # Check cache was attempted to be set (decorator behavior)
    mock_redis_client.set.assert_called_once()
    
    # Check tracker was updated
    mock_tracker_instance.update_agent_status.assert_called_once()