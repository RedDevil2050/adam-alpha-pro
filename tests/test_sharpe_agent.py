import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import pandas as pd
import numpy as np
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import date, timedelta

# Assume the agent exists at this location
try:
    from backend.agents.risk.sharpe_agent import run as sharpe_run, agent_name
except ImportError:
    pytest.skip("Sharpe agent not found, skipping tests", allow_module_level=True)

# Use the imported agent_name if available, otherwise define it
if 'agent_name' not in locals():
    agent_name = "sharpe_agent"

@pytest.mark.asyncio
@patch('backend.agents.decorators.get_tracker')
@patch('backend.agents.decorators.get_redis_client')
@patch('backend.agents.risk.sharpe_agent.fetch_price_series') # Patch where fetch_price_series is used
async def test_sharpe_agent_basic(
    mock_fetch_prices,
    mock_get_redis,
    mock_get_tracker
):
    # --- Mock Configuration ---
    symbol = "TEST_SHARPE"
    num_periods = 252 + 5 # Need enough data for annualization + buffer

    # Create price data simulating a steady upward trend
    prices = np.linspace(100, 120, num_periods) # 20% return over the period
    price_series = pd.Series(prices, index=pd.date_range(end=date.today(), periods=num_periods, freq='B')) # Business days

    # 1. Mock fetch_price_series
    mock_fetch_prices.return_value = price_series

    # 2. Mock Redis
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get.return_value = None # Cache miss
    mock_redis_instance.set = AsyncMock()
    mock_get_redis.return_value = mock_redis_instance

    # 3. Mock Tracker
    mock_tracker_instance = AsyncMock()
    mock_tracker_instance.update_agent_status = AsyncMock()
    mock_get_tracker.return_value = mock_tracker_instance

    # --- Expected Results (Conceptual) ---
    # For a steady uptrend with low volatility, expect a positive Sharpe Ratio
    # The exact value depends on the risk-free rate assumption in the agent (e.g., 0.02)
    # Let's assume a positive value and a corresponding verdict
    expected_verdict_positive = "GOOD_RISK_ADJUSTED_RETURN" # Example verdict

    # --- Run Agent ---
    result = await sharpe_run(symbol)

    # --- Assertions ---
    assert result['symbol'] == symbol
    assert result['agent_name'] == agent_name
    assert result.get('error') is None, f"Agent returned error: {result.get('error')}"

    # Check core fields exist
    assert 'verdict' in result
    assert 'confidence' in result
    assert 'value' in result # This should be the Sharpe Ratio
    assert 'details' in result
    assert 'sharpe_ratio' in result['details']

    # Assertions based on expected positive outcome
    assert result['value'] > 0 # Expect positive Sharpe for steady uptrend
    assert result['details']['sharpe_ratio'] == result['value']
    # assert result['verdict'] == expected_verdict_positive # Verdict depends on agent's thresholds

    # --- Verify Mocks ---
    mock_fetch_prices.assert_awaited_once_with(symbol)
    mock_get_redis.assert_awaited_once()
    mock_redis_instance.get.assert_awaited_once()
    # Decorator should cache successful results
    if result.get('verdict') not in ['ERROR', 'NO_DATA']:
        mock_redis_instance.set.assert_awaited_once()
    mock_get_tracker.assert_called_once()
    mock_tracker_instance.update_agent_status.assert_awaited_once()

