import pytest
from unittest.mock import AsyncMock, patch, MagicMock # Import MagicMock
from backend.agents.automation.alert_engine_agent import run as alert_run, agent_name
import json # Import json for cache serialization

# Mock data
SYMBOL = "TEST"
MOCK_PRICES = [100.0, 101.0, 102.0] * 20 # 60 days
# Adjusted MOCK_EPS to ensure QoQ growth > 10% (e.g., 1.0 -> 1.2 is 20%)
MOCK_EPS = [1.0, 1.0, 1.2] # Example EPS data
MOCK_EARNINGS_OUTPUT = {"details": {"days_to_event": 5}}
MOCK_CORP_OUTPUT = {"details": {"actions": ["Dividend"]}}
MOCK_CORP_OUTPUT_NONE = {"details": {"actions": []}}

# Use pytest fixture for mock redis client to ensure isolation between tests
@pytest.fixture(autouse=True)
def mock_redis():
    # Create a new mock for each test
    mock_client = AsyncMock()
    mock_client.get.return_value = None # Default: cache miss
    mock_client.set.return_value = True
    with patch('backend.agents.automation.alert_engine_agent.get_redis_client', return_value=mock_client):
        yield mock_client # Provide the mock client to the test if needed

# Remove the redundant @patch for get_redis_client from each test

@pytest.mark.asyncio
# Correct patch targets to where they are used within the alert_engine_agent module
@patch('backend.agents.automation.alert_engine_agent.corp_run', new_callable=AsyncMock)
@patch('backend.agents.automation.alert_engine_agent.earnings_run', new_callable=AsyncMock)
@patch('backend.agents.automation.alert_engine_agent.fetch_eps_data', new_callable=AsyncMock)
@patch('backend.agents.automation.alert_engine_agent.fetch_price_series', new_callable=AsyncMock)
async def test_alert_engine_generates_alerts(
    mock_fetch_prices, mock_fetch_eps, mock_earnings, mock_corp, mock_redis # mock_redis is now injected by fixture
):
    # Arrange
    # mock_redis fixture handles cache miss setup
    # Mock data provider functions
    mock_fetch_prices.return_value = MOCK_PRICES
    mock_fetch_eps.return_value = MOCK_EPS # Use adjusted EPS
    # Mock agent runs
    mock_earnings.return_value = MOCK_EARNINGS_OUTPUT
    mock_corp.return_value = MOCK_CORP_OUTPUT

    # Act
    result = await alert_run(SYMBOL)

    # Assert
    assert result["symbol"] == SYMBOL
    assert result["agent_name"] == agent_name
    assert result["verdict"] == "ALERT"
    assert "Above 50DMA" in result["details"]["alerts"] # Assuming 102 > MA of [100,101,102]*20
    assert "EPS QoQ >10%" in result["details"]["alerts"] # (1.2 - 1.0) / 1.0 = 0.2 > 0.1
    assert "Earnings within 7d" in result["details"]["alerts"] # days_to_event = 5
    assert "Corporate Actions" in result["details"]["alerts"] # actions = ["Dividend"]
    assert result["confidence"] == 1.0 # 4 alerts / 4
    assert result["value"] == 4
    # Verify cache set was called once
    mock_redis.set.assert_awaited_once()


@pytest.mark.asyncio
# Correct patch targets
@patch('backend.agents.automation.alert_engine_agent.corp_run', new_callable=AsyncMock)
@patch('backend.agents.automation.alert_engine_agent.earnings_run', new_callable=AsyncMock)
@patch('backend.agents.automation.alert_engine_agent.fetch_eps_data', new_callable=AsyncMock)
@patch('backend.agents.automation.alert_engine_agent.fetch_price_series', new_callable=AsyncMock)
async def test_alert_engine_no_alerts(
    mock_fetch_prices, mock_fetch_eps, mock_earnings, mock_corp, mock_redis # mock_redis injected
):
    # Arrange
    # mock_redis fixture handles cache miss setup
    # Mock data that won't trigger alerts
    prices_below_ma = [100.0] * 60 # Price below MA (MA=100, Price=100 -> not > MA)
    eps_flat = [1.0, 1.0, 1.0]
    earnings_far = {"details": {"days_to_event": 30}} # Define earnings_far here
    corp_none = {"details": {"actions": []}} # Define corp_none here

    mock_fetch_prices.return_value = prices_below_ma
    mock_fetch_eps.return_value = eps_flat
    mock_earnings.return_value = earnings_far
    mock_corp.return_value = corp_none

    # Act
    result = await alert_run(SYMBOL)

    # Assert
    assert result["symbol"] == SYMBOL
    assert result["agent_name"] == agent_name
    assert result["verdict"] == "NO_ALERT"
    assert not result["details"]["alerts"] # No alerts generated
    assert result["confidence"] == 0.0
    assert result["value"] == 0
    mock_redis.set.assert_awaited_once() # Verify set called once

@pytest.mark.asyncio
# Correct patch targets
@patch('backend.agents.automation.alert_engine_agent.corp_run', new_callable=AsyncMock)
@patch('backend.agents.automation.alert_engine_agent.earnings_run', new_callable=AsyncMock)
@patch('backend.agents.automation.alert_engine_agent.fetch_eps_data', new_callable=AsyncMock)
@patch('backend.agents.automation.alert_engine_agent.fetch_price_series', new_callable=AsyncMock)
async def test_alert_engine_partial_data(
    mock_fetch_prices, mock_fetch_eps, mock_earnings, mock_corp, mock_redis # mock_redis injected
):
    # Arrange
    # mock_redis fixture handles cache miss setup
    # Define variables needed in this test scope
    earnings_far = {"details": {"days_to_event": 30}} # Define earnings_far here
    corp_none = {"details": {"actions": []}} # Define corp_none here
    # Simulate missing EPS data
    mock_fetch_prices.return_value = MOCK_PRICES # Price triggers alert
    mock_fetch_eps.return_value = None # No EPS data
    mock_earnings.return_value = earnings_far # No earnings alert
    mock_corp.return_value = corp_none # No corp action alert

    # Act
    result = await alert_run(SYMBOL)

    # Assert
    assert result["symbol"] == SYMBOL
    assert result["agent_name"] == agent_name
    assert result["verdict"] == "ALERT"
    assert len(result["details"]["alerts"]) == 1
    assert "Above 50DMA" in result["details"]["alerts"]
    assert result["confidence"] == 0.25 # 1 alert / 4
    assert result["value"] == 1
    assert result["details"]["eps_growth"] is None # Check detail is None
    mock_redis.set.assert_awaited_once() # Verify set called once

@pytest.mark.asyncio
# No other patches needed, only redis
async def test_alert_engine_cache_hit(mock_redis): # mock_redis injected
    # Arrange
    # Simulate cache hit by configuring the mock from the fixture
    cached_result = {"symbol": SYMBOL, "verdict": "CACHED_ALERT", "confidence": 0.99}
    # The agent code expects json string from redis.get
    mock_redis.get.return_value = json.dumps(cached_result)

    # Act
    result = await alert_run(SYMBOL)

    # Assert
    assert result == cached_result # Should return cached result directly
    mock_redis.get.assert_awaited_once_with(f"{agent_name}:{SYMBOL}")
    mock_redis.set.assert_not_awaited() # Set should not be called on cache hit