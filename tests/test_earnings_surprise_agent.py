import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
# Import the agent's run function
from backend.agents.event.earnings_surprise_agent import run as es_run

agent_name = "earnings_surprise_agent"

@pytest.mark.asyncio
# Patch dependencies
@patch('backend.agents.decorators.get_tracker')
@patch('backend.agents.decorators.get_redis_client')
@patch('backend.agents.event.earnings_surprise_agent.fetch_earnings_calendar')
async def test_earnings_surprise_positive(
    mock_fetch_earnings,
    mock_get_redis,
    mock_get_tracker
):
    # --- Mock Configuration ---
    symbol = "TEST_POS"
    threshold_pct = 5.0 # Assume default threshold
    actual_eps = 1.10
    estimated_eps = 1.00
    report_date = "2025-04-15"

    # 1. Mock fetch_earnings_calendar
    # Return data for the most recent report having actual and estimated
    mock_earnings_data = [
        {
            "reportDate": report_date,
            "actualEPS": actual_eps,
            "estimatedEPS": estimated_eps
        },
        {
            "reportDate": "2025-01-15",
            "actualEPS": 0.95,
            "estimatedEPS": 0.90
        }
        # Add more older data if needed
    ]
    mock_fetch_earnings.return_value = mock_earnings_data

    # 2. Mock Redis
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get.return_value = None # Cache miss
    mock_redis_instance.set = AsyncMock()
    mock_get_redis.return_value = mock_redis_instance

    # 3. Mock Tracker
    mock_tracker_instance = AsyncMock()
    mock_tracker_instance.update_agent_status = AsyncMock()
    mock_get_tracker.return_value = mock_tracker_instance

    # --- Expected Results ---
    expected_surprise_pct = ((actual_eps - estimated_eps) / abs(estimated_eps)) * 100 # (1.10 - 1.00) / 1.00 * 100 = 10.0
    expected_verdict = "POSITIVE_SURPRISE" # Since 10.0 > 5.0
    # Example confidence scaling: min(0.95, 0.6 + (10.0 / (5.0 * 5))) = min(0.95, 0.6 + 0.4) = 0.95
    expected_confidence = 0.95

    # --- Run Agent ---
    result = await es_run(symbol)

    # --- Assertions ---
    assert result['symbol'] == symbol
    assert result['agent_name'] == agent_name
    assert result['verdict'] == expected_verdict
    assert result['confidence'] == pytest.approx(expected_confidence)
    assert result['value'] == pytest.approx(expected_surprise_pct)
    assert result.get('error') is None

    # Check details
    assert 'details' in result
    details = result['details']
    assert details['actual_eps'] == pytest.approx(actual_eps)
    assert details['estimated_eps'] == pytest.approx(estimated_eps)
    assert details['report_date'] == report_date
    assert details['surprise_pct'] == pytest.approx(expected_surprise_pct)
    assert details['threshold_pct'] == threshold_pct

    # --- Verify Mocks ---
    mock_fetch_earnings.assert_awaited_once_with(symbol, lookback_days=90)
    mock_get_redis.assert_awaited_once()
    mock_redis_instance.get.assert_awaited_once()
    mock_redis_instance.set.assert_awaited_once()
    mock_get_tracker.assert_called_once()
    mock_tracker_instance.update_agent_status.assert_awaited_once()

@pytest.mark.asyncio
# Patch dependencies
@patch('backend.agents.decorators.get_tracker')
@patch('backend.agents.decorators.get_redis_client')
@patch('backend.agents.event.earnings_surprise_agent.fetch_earnings_calendar')
async def test_earnings_surprise_negative(
    mock_fetch_earnings,
    mock_get_redis,
    mock_get_tracker
):
    # --- Mock Configuration ---
    symbol = "TEST_NEG"
    threshold_pct = 5.0
    actual_eps = 0.90
    estimated_eps = 1.00
    report_date = "2025-04-16"

    mock_fetch_earnings.return_value = [
        {"reportDate": report_date, "actualEPS": actual_eps, "estimatedEPS": estimated_eps}
    ]
    mock_redis_instance = AsyncMock(get=AsyncMock(return_value=None), set=AsyncMock())
    mock_get_redis.return_value = mock_redis_instance
    mock_tracker_instance = AsyncMock(update_agent_status=AsyncMock())
    mock_get_tracker.return_value = mock_tracker_instance

    # --- Expected Results ---
    expected_surprise_pct = ((0.90 - 1.00) / abs(1.00)) * 100 # -10.0
    expected_verdict = "NEGATIVE_SURPRISE" # Since -10.0 < -5.0
    expected_confidence = 0.95 # min(0.95, 0.6 + (abs(-10.0) / (5.0 * 5))) = 0.95

    result = await es_run(symbol)

    assert result['verdict'] == expected_verdict
    assert result['confidence'] == pytest.approx(expected_confidence)
    assert result['value'] == pytest.approx(expected_surprise_pct)
    assert result['details']['surprise_pct'] == pytest.approx(expected_surprise_pct)

@pytest.mark.asyncio
# Patch dependencies
@patch('backend.agents.decorators.get_tracker')
@patch('backend.agents.decorators.get_redis_client')
@patch('backend.agents.event.earnings_surprise_agent.fetch_earnings_calendar')
async def test_earnings_surprise_inline(
    mock_fetch_earnings,
    mock_get_redis,
    mock_get_tracker
):
    # --- Mock Configuration ---
    symbol = "TEST_INLINE"
    threshold_pct = 5.0
    actual_eps = 1.02
    estimated_eps = 1.00
    report_date = "2025-04-17"

    mock_fetch_earnings.return_value = [
        {"reportDate": report_date, "actualEPS": actual_eps, "estimatedEPS": estimated_eps}
    ]
    mock_redis_instance = AsyncMock(get=AsyncMock(return_value=None), set=AsyncMock())
    mock_get_redis.return_value = mock_redis_instance
    mock_tracker_instance = AsyncMock(update_agent_status=AsyncMock())
    mock_get_tracker.return_value = mock_tracker_instance

    # --- Expected Results ---
    expected_surprise_pct = ((1.02 - 1.00) / abs(1.00)) * 100 # 2.0
    expected_verdict = "IN_LINE" # Since -5.0 < 2.0 < 5.0
    expected_confidence = 0.5

    result = await es_run(symbol)

    assert result['verdict'] == expected_verdict
    assert result['confidence'] == pytest.approx(expected_confidence)
    assert result['value'] == pytest.approx(expected_surprise_pct)
    assert result['details']['surprise_pct'] == pytest.approx(expected_surprise_pct)
