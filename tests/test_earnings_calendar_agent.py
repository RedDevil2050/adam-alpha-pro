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
@patch('backend.agents.decorators.get_tracker') # Tracker used by decorator
@patch('backend.utils.cache_utils.get_redis_client', new_callable=AsyncMock) # Redis client used by decorator
@patch('backend.agents.event.earnings_calendar_agent.fetch_earnings_calendar') # Data fetching function used by agent
async def test_earnings_calendar_agent_upcoming_event(
    mock_fetch_earnings,
    mock_decorator_get_redis, # Mock for backend.utils.cache_utils.get_redis_client
    mock_decorator_get_tracker, # Mock for backend.agents.decorators.get_tracker
    monkeypatch
):
    # --- Mock Configuration ---
    symbol = 'XYZ'
    # 1. Mock fetch_earnings_calendar to return an upcoming date
    upcoming_date_str = "2025-05-08"
    mock_fetch_earnings.return_value = {"nextEarningsDate": upcoming_date_str}

    # 2. Mock Redis (used by decorator)
    mock_redis_instance_for_decorator = AsyncMock()
    mock_redis_instance_for_decorator.get = AsyncMock(return_value=None) # Cache miss for decorator
    mock_redis_instance_for_decorator.set = AsyncMock()
    mock_decorator_get_redis.return_value = mock_redis_instance_for_decorator

    # 3. Mock Tracker (used by decorator)
    mock_tracker_instance_for_decorator = AsyncMock()
    mock_tracker_instance_for_decorator.update_agent_status = AsyncMock() # Mock the async method
    mock_decorator_get_tracker.return_value = mock_tracker_instance_for_decorator

    # --- Expected Results ---
    expected_verdict = "UPCOMING" # Since days <= 7
    expected_confidence = 1.0 # Based on agent logic for <= 7 days
    # Agent returns the date string as value, not days to event
    expected_value = upcoming_date_str 

    # --- Run Agent ---
    # Need to patch datetime.date.today() to control the 'current date'
    # Although current agent doesn't use it for date diff, good for future-proofing
    with patch('backend.agents.event.earnings_calendar_agent.datetime') as mock_datetime:
        mock_datetime.date.today.return_value = datetime.date(2025, 5, 3)
        # Ensure strptime is available if the agent were to parse dates
        mock_datetime.datetime.strptime = datetime.datetime.strptime 
        res = await ec_run(symbol)

    # --- Assertions ---
    assert res['symbol'] == symbol
    assert res['agent_name'] == agent_name
    assert res['verdict'] == expected_verdict
    assert res['confidence'] == pytest.approx(expected_confidence)
    assert res['value'] == expected_value # Check against the date string
    assert res.get('error') is None
    assert 'details' in res
    # Agent stores the date under 'nextEarningsDate' in details
    assert res['details']['nextEarningsDate'] == upcoming_date_str
    # Agent does not calculate or store 'days_to_event'
    # assert res['details']['days_to_event'] == expected_days

    # --- Verify Mocks ---
    mock_fetch_earnings.assert_awaited_once_with(symbol)
    mock_decorator_get_redis.assert_awaited_once() # Decorator called its get_redis_client
    mock_redis_instance_for_decorator.get.assert_awaited_once_with(f"{agent_name}:{symbol}")
    # Ensure cache set is awaited if the verdict is not ERROR/NO_DATA
    if res['verdict'] not in ["ERROR", "NO_DATA", None]:
        mock_redis_instance_for_decorator.set.assert_awaited_once()
    else:
        mock_redis_instance_for_decorator.set.assert_not_awaited() # Should not be called for NO_DATA/ERROR from agent

    mock_decorator_get_tracker.assert_called_once() # Decorator called its get_tracker
    mock_tracker_instance_for_decorator.update_agent_status.assert_awaited_once() # Decorator updated status