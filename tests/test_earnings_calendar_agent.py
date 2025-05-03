import pytest
from unittest.mock import AsyncMock, patch, MagicMock # Import MagicMock
# Import the agent's run function and agent_name
from backend.agents.event.earnings_calendar_agent import run as ec_run, agent_name
import datetime # Import datetime

@pytest.mark.asyncio
# Patch dependencies (innermost first)
# Correct patch target for tracker.update
@patch('backend.agents.event.earnings_calendar_agent.tracker.update', new_callable=MagicMock)
# Correct patch target for redis client used directly by the agent
@patch('backend.agents.event.earnings_calendar_agent.get_redis_client')
# Patch the data fetching function
@patch('backend.agents.event.earnings_calendar_agent.fetch_earnings_calendar')
async def test_earnings_calendar_agent_no_data(
    mock_fetch_earnings, # Renamed mock
    mock_get_redis,
    mock_tracker_update, # Add tracker mock to args
    monkeypatch # Keep monkeypatch if needed
):
    # --- Mock Configuration ---
    symbol = 'ABC'
    # 1. Mock fetch_earnings_calendar to return no data (empty dict)
    mock_fetch_earnings.return_value = {}

    # 2. Set up Redis mock instance
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get = AsyncMock(return_value=None) # Simulate cache miss
    mock_redis_instance.set = AsyncMock()
    mock_get_redis.return_value = mock_redis_instance

    # 3. Mock Tracker update (already patched with MagicMock)
    mock_tracker_update.return_value = None # Synchronous mock

    # --- Run Agent ---
    res = await ec_run(symbol)

    # --- Assertions for NO_DATA case ---
    assert res['symbol'] == symbol
    assert res['agent_name'] == agent_name
    assert res['verdict'] == 'NO_DATA'
    assert res['value'] is None
    assert res['details'] == {} # Expect empty details for NO_DATA
    assert res.get('error') is None

    # --- Verify Mocks ---
    mock_fetch_earnings.assert_awaited_once_with(symbol)
    mock_get_redis.assert_awaited_once() # Verify redis client factory was awaited
    mock_redis_instance.get.assert_awaited_once_with(f"{agent_name}:{symbol}") # Check cache key
    # Cache set should be called even for NO_DATA
    mock_redis_instance.set.assert_awaited_once()
    # Verify tracker update was called
    mock_tracker_update.assert_called_once_with("event", agent_name, "implemented")


@pytest.mark.asyncio
# Patch dependencies
@patch('backend.agents.event.earnings_calendar_agent.tracker.update', new_callable=MagicMock)
@patch('backend.agents.event.earnings_calendar_agent.get_redis_client')
@patch('backend.agents.event.earnings_calendar_agent.fetch_earnings_calendar')
async def test_earnings_calendar_agent_upcoming_event(
    mock_fetch_earnings,
    mock_get_redis,
    mock_tracker_update,
    monkeypatch
):
    # --- Mock Configuration ---
    symbol = 'XYZ'
    # 1. Mock fetch_earnings_calendar to return an upcoming date
    # Simulate today is May 3, 2025. Event is May 8, 2025 (5 days away)
    upcoming_date_str = "2025-05-08"
    mock_fetch_earnings.return_value = {"next_earnings_date": upcoming_date_str}
    expected_days = 5

    # 2. Mock Redis
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get = AsyncMock(return_value=None)
    mock_redis_instance.set = AsyncMock()
    mock_get_redis.return_value = mock_redis_instance

    # 3. Mock Tracker update
    mock_tracker_update.return_value = None

    # --- Expected Results ---
    expected_verdict = "UPCOMING" # Since days <= 7
    expected_confidence = 1.0 # Based on agent logic for <= 7 days
    expected_value = expected_days

    # --- Run Agent ---
    # Need to patch datetime.date.today() to control the 'current date'
    with patch('backend.agents.event.earnings_calendar_agent.datetime') as mock_datetime:
        mock_datetime.date.today.return_value = datetime.date(2025, 5, 3)
        mock_datetime.strptime = datetime.datetime.strptime # Keep strptime working
        res = await ec_run(symbol)

    # --- Assertions ---
    assert res['symbol'] == symbol
    assert res['agent_name'] == agent_name
    assert res['verdict'] == expected_verdict
    assert res['confidence'] == pytest.approx(expected_confidence)
    assert res['value'] == expected_value
    assert res.get('error') is None
    assert 'details' in res
    assert res['details']['next_earnings_date'] == upcoming_date_str
    assert res['details']['days_to_event'] == expected_days

    # --- Verify Mocks ---
    mock_fetch_earnings.assert_awaited_once_with(symbol)
    mock_get_redis.assert_awaited_once()
    mock_redis_instance.get.assert_awaited_once_with(f"{agent_name}:{symbol}")
    mock_redis_instance.set.assert_awaited_once()
    mock_tracker_update.assert_called_once_with("event", agent_name, "implemented")