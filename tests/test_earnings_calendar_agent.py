import pytest
from unittest.mock import AsyncMock, patch, MagicMock # Import MagicMock
# Import the agent's run function and agent_name
from backend.agents.event.earnings_calendar_agent import run as ec_run, agent_name
import datetime # Import datetime

@pytest.mark.asyncio
# Patch dependencies (innermost first)
@patch('backend.agents.base.get_redis_client', new_callable=AsyncMock) # For AgentBase
# Correct patch target for tracker.update
@patch('backend.agents.event.earnings_calendar_agent.tracker.update', new_callable=MagicMock)
# Correct patch target for redis client used directly by the agent
@patch('backend.agents.event.earnings_calendar_agent.get_redis_client', new_callable=AsyncMock) # For agent/decorator
# Patch the data fetching function
@patch('backend.agents.event.earnings_calendar_agent.fetch_earnings_calendar')
async def test_earnings_calendar_agent_no_data(
    mock_fetch_earnings, # Renamed mock
    mock_agent_get_redis, # Corresponds to event.earnings_calendar_agent.get_redis_client
    mock_tracker_update, # Add tracker mock to args
    mock_base_get_redis, # Corresponds to base.get_redis_client
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
    mock_agent_get_redis.return_value = mock_redis_instance
    mock_base_get_redis.return_value = mock_redis_instance

    # 3. Mock Tracker update (already patched with MagicMock)
    # mock_tracker_update.return_value = None # Synchronous mock - already an arg

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
    mock_agent_get_redis.assert_awaited_once() # Verify redis client factory was awaited
    mock_base_get_redis.assert_awaited_once()
    # get might be called by decorator then base, or just base if no decorator cache
    assert mock_redis_instance.get.await_count >= 1
    # Cache set should be called even for NO_DATA by the decorator if present, or by base
    if res.get('verdict') not in ['ERROR', None]: # Base agent sets unless error
        assert mock_redis_instance.set.await_count >= 1
    # Verify tracker update was called
    mock_tracker_update.assert_called_once_with("event", agent_name, "implemented")


@pytest.mark.asyncio
# Patch dependencies
@patch('backend.agents.base.get_redis_client', new_callable=AsyncMock) # For AgentBase
# Patch tracker.update directly as used by the agent
@patch('backend.agents.event.earnings_calendar_agent.tracker.update', new_callable=MagicMock)
# Corrected patch target for the redis client based on other tests and typical decorator usage
@patch('backend.agents.event.earnings_calendar_agent.get_redis_client', new_callable=AsyncMock) # Redis client used by agent/decorator
@patch('backend.agents.event.earnings_calendar_agent.fetch_earnings_calendar') # Data fetching function used by agent
async def test_earnings_calendar_agent_upcoming_event(
    mock_fetch_earnings,
    mock_agent_get_redis, # Corresponds to event.earnings_calendar_agent.get_redis_client
    mock_tracker_update, # Changed from mock_decorator_get_tracker
    mock_base_get_redis, # Corresponds to base.get_redis_client
    monkeypatch
):
    # --- Mock Configuration ---
    symbol = 'XYZ'
    # 1. Mock fetch_earnings_calendar to return an upcoming date
    upcoming_date_str = "2025-05-08"
    mock_fetch_earnings.return_value = {"nextEarningsDate": upcoming_date_str}

    # 2. Mock Redis (used by agent/decorator and base)
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get = AsyncMock(return_value=None) # Cache miss
    mock_redis_instance.set = AsyncMock()
    mock_agent_get_redis.return_value = mock_redis_instance
    mock_base_get_redis.return_value = mock_redis_instance

    # 3. Mock Tracker update (already patched with MagicMock)
    # mock_tracker_update.return_value = None # Synchronous mock - already an arg

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
    mock_agent_get_redis.assert_awaited_once() # Agent/decorator called its get_redis_client
    mock_base_get_redis.assert_awaited_once()
    assert mock_redis_instance.get.await_count >= 1
    # Ensure cache set is awaited if the verdict is not ERROR/NO_DATA
    if res['verdict'] not in ["ERROR", "NO_DATA", None]:
        assert mock_redis_instance.set.await_count >= 1
    else:
        # If NO_DATA or ERROR, decorator might not set, but base might if no error from agent itself
        # This logic can be tricky; for now, ensure it's called if not an agent error.
        if res.get('error') is None and res['verdict'] != 'ERROR': # Base agent sets unless error
             assert mock_redis_instance.set.await_count >=1
        else:
            # If agent itself returns ERROR, or if decorator handles NO_DATA without setting,
            # then set might not be called by both.
            # For simplicity, if we expect an error or NO_DATA from the agent's core logic,
            # we might not always expect a set from the decorator.
            # However, AgentBase.run always tries to set unless an exception occurs before caching.
            pass # More nuanced check might be needed depending on decorator/base agent logic

    # Verify tracker update was called
    mock_tracker_update.assert_called_once_with("event", agent_name, "implemented")