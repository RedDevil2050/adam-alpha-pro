import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import pytest
import pandas as pd # Import pandas
from backend.agents.automation.bulk_portfolio_agent import run as bp_run
from unittest.mock import AsyncMock, patch # Import patch

# Define agent_name if used in assertions or mocks
agent_name = "bulk_portfolio_agent"

@pytest.mark.asyncio
# Patch dependencies used by the agent
@patch('backend.agents.automation.bulk_portfolio_agent.tracker') # Patch tracker
@patch('backend.agents.automation.bulk_portfolio_agent.get_redis_client', new_callable=AsyncMock) # Patch redis
@patch('backend.agents.automation.bulk_portfolio_agent.run_full_cycle', new_callable=AsyncMock) # Patch run_full_cycle
@patch('backend.agents.automation.bulk_portfolio_agent.fetch_price_series', new_callable=AsyncMock) # Patch fetch_price_series
async def test_bulk_portfolio_agent(
    mock_fetch_prices,
    mock_run_cycle,
    mock_get_redis,
    mock_tracker,
    monkeypatch # Keep monkeypatch if needed, though patch decorator is often cleaner
):
    # --- Mock Configuration ---
    test_symbols = ['AAPL', 'GOOG']

    # 1. Mock fetch_price_series (called once for the first symbol)
    # Return a pandas Series to match agent's expectation (e.g., checking .empty)
    mock_fetch_prices.return_value = pd.Series([150.0, 151.0]) # Example price data as a Series

    # 2. Mock run_full_cycle (called for each symbol)
    # Simulate different results for different symbols
    # run_full_cycle should return a dictionary directly
    mock_run_cycle.side_effect = [
        {'verdict': 'BUY', 'score': 0.8}, # Result for AAPL
        {'verdict': 'HOLD', 'score': 0.5}  # Result for GOOG
    ]

    # 3. Mock Redis
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get.return_value = None # Cache miss
    mock_redis_instance.set = AsyncMock()
    mock_get_redis.return_value = mock_redis_instance

    # 4. Mock Tracker
    # The agent calls tracker.update directly
    mock_tracker.update = AsyncMock()

    # --- Run Agent ---
    # Pass the list of symbols
    res = await bp_run(test_symbols)

    # --- Assertions ---
    assert isinstance(res, dict)
    assert res['agent_name'] == agent_name
    assert res['verdict'] == 'COMPLETED'
    assert res['value'] == len(test_symbols) # Should be the number of symbols processed
    assert 'details' in res
    details = res['details']
    assert 'avg_score' in details
    assert 'buy_count' in details
    assert 'per_symbol' in details
    assert len(details['per_symbol']) == len(test_symbols)

    # Check calculations based on mocked run_full_cycle results
    expected_avg_score = (0.8 + 0.5) / 2
    expected_buy_count = 1
    assert details['avg_score'] == pytest.approx(expected_avg_score)
    assert details['buy_count'] == expected_buy_count
    assert res['confidence'] == pytest.approx(expected_avg_score) # Confidence is avg_score
    assert res['score'] == pytest.approx(expected_avg_score) # Score is also avg_score

    # Check per-symbol details
    assert 'AAPL' in details['per_symbol']
    assert details['per_symbol']['AAPL']['verdict'] == 'BUY'
    assert details['per_symbol']['AAPL']['score'] == 0.8
    assert 'GOOG' in details['per_symbol']
    assert details['per_symbol']['GOOG']['verdict'] == 'HOLD'
    assert details['per_symbol']['GOOG']['score'] == 0.5

    # --- Verify Mocks ---
    # fetch_price_series is called once for the first symbol as an initial check
    assert mock_fetch_prices.call_count == 1
    mock_fetch_prices.assert_any_await(test_symbols[0], source_preference=["api", "scrape"])

    assert mock_run_cycle.call_count == len(test_symbols)
    # The agent calls run_full_cycle with a single symbol string, not a list
    mock_run_cycle.assert_any_await('AAPL')
    mock_run_cycle.assert_any_await('GOOG')

    mock_get_redis.assert_awaited_once()
    # Verify that set was called on the redis mock if cache was missed and data processed
    if mock_redis_instance.get.return_value is None and res.get("verdict") != "ERROR":
        mock_redis_instance.set.assert_awaited_once()
    else:
        mock_redis_instance.set.assert_not_awaited() # Ensure it's not awaited if not set

    # Check tracker update call
    mock_tracker.update.assert_awaited_once_with("automation", agent_name, "implemented")