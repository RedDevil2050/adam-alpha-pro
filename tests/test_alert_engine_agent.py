import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import pytest
import pandas as pd
import numpy as np # Import numpy
import json # Import json
from unittest.mock import AsyncMock, patch
from backend.agents.automation.alert_engine_agent import run as alert_run, agent_name

@pytest.mark.asyncio
# Patch dependencies used by the agent and its decorators
@patch('backend.agents.automation.alert_engine_agent.tracker.update')
@patch('backend.agents.automation.alert_engine_agent.get_redis_client')
@patch('backend.agents.automation.alert_engine_agent.corp_run')
@patch('backend.agents.automation.alert_engine_agent.earnings_run')
@patch('backend.agents.automation.alert_engine_agent.fetch_eps_data')
@patch('backend.agents.automation.alert_engine_agent.fetch_price_series')
async def test_alert_engine_agent(
    mock_fetch_prices, 
    mock_fetch_eps, 
    mock_earnings_run, 
    mock_corp_run, 
    mock_get_redis, 
    mock_tracker_update,
    monkeypatch # Keep monkeypatch if needed for settings
):
    # --- Mock Configuration ---
    symbol = 'ABC'
    # 1. Mock fetch_price_series: Return a list of 60 prices, ending above MA50
    prices = list(np.linspace(90, 105, 60)) # Ends at 105
    mock_fetch_prices.return_value = prices
    # Expected MA50 (approximate mean of last 50 points)
    expected_ma50 = np.mean(prices[-50:]) # ~ mean(93 to 105)

    # 2. Mock fetch_eps_data: Return EPS data showing >10% growth
    eps_data = [1.0, 1.2] # 20% growth
    mock_fetch_eps.return_value = eps_data
    expected_eps_growth = 0.2

    # 3. Mock earnings_run: Return earnings within 7 days
    earnings_result = {"details": {"days_to_event": 5}}
    mock_earnings_run.return_value = earnings_result
    expected_days_to_earn = 5

    # 4. Mock corp_run: Return some corporate actions
    corp_result = {"details": {"actions": ["Dividend"]}}
    mock_corp_run.return_value = corp_result

    # 5. Mock Redis
    mock_redis_instance = AsyncMock()
    # Simulate cache miss, return None for get
    # Important: Redis stores JSON strings, so get should return None or a JSON string
    mock_redis_instance.get.return_value = None 
    mock_redis_instance.set = AsyncMock()
    mock_get_redis.return_value = mock_redis_instance

    # 6. Mock Tracker (already patched)
    mock_tracker_update.return_value = None

    # --- Expected Alerts ---
    # Based on mocks: Above 50DMA, EPS QoQ >10%, Earnings within 7d, Corporate Actions
    expected_alerts = ["Above 50DMA", "EPS QoQ >10%", "Earnings within 7d", "Corporate Actions"]
    expected_verdict = "ALERT"
    expected_confidence = 1.0 # 4 alerts / 4 = 1.0
    expected_value = 4 # Number of alerts

    # --- Run Agent ---
    res = await alert_run(symbol, {})

    # --- Assertions ---
    assert isinstance(res, dict)
    assert res['symbol'] == symbol
    assert res['agent_name'] == agent_name
    assert res['verdict'] == expected_verdict
    assert res['confidence'] == pytest.approx(expected_confidence)
    assert res['value'] == expected_value
    assert res.get('error') is None
    assert 'details' in res
    details = res['details']
    assert details['alerts'] == expected_alerts
    assert details['ma50'] == pytest.approx(expected_ma50, abs=0.1) # Allow slight tolerance
    assert details['eps_growth'] == pytest.approx(expected_eps_growth)
    assert details['earnings_in'] == expected_days_to_earn

    # --- Verify Mocks ---
    mock_fetch_prices.assert_awaited_once_with(symbol, source_preference=["api", "scrape"])
    mock_fetch_eps.assert_awaited_once_with(symbol)
    mock_earnings_run.assert_awaited_once_with(symbol)
    mock_corp_run.assert_awaited_once_with(symbol)
    mock_get_redis.assert_awaited_once()
    mock_redis_instance.get.assert_awaited_once_with(f"{agent_name}:{symbol}")
    # Check that set was called with a JSON string
    mock_redis_instance.set.assert_awaited_once()
    call_args, call_kwargs = mock_redis_instance.set.call_args
    assert call_args[0] == f"{agent_name}:{symbol}" # key
    assert isinstance(call_args[1], str) # value should be string
    assert json.loads(call_args[1]) == res # Check if the string decodes to the result
    assert 'ex' in call_kwargs # Check TTL was set
    mock_tracker_update.assert_called_once_with("automation", agent_name, "implemented")