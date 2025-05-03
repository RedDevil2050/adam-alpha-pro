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
    # Assuming agent_name is defined in the agent file
except ImportError:
    pytest.skip("Sharpe agent not found, skipping tests", allow_module_level=True)

# Use the imported agent_name if available, otherwise define it
if 'agent_name' not in locals():
    agent_name = "sharpe_agent"

# Define constants likely used by the agent (adjust if agent uses different values)
ANNUAL_RISK_FREE_RATE = 0.02  # Common assumption, e.g., 2%
ANNUALIZATION_FACTOR = 252   # Common for daily data (business days)

# Define expected verdict thresholds for Sharpe Ratio (example values)
# Adjust these based on your agent's actual logic
SHARPE_THRESHOLDS = {
    "GOOD_RISK_ADJUSTED_RETURN": 1.0,   # Sharpe > 1 is often considered good
    "AVERAGE_RISK_ADJUSTED_RETURN": 0.5, # Sharpe between 0.5 and 1
    "POOR_RISK_ADJUSTED_RETURN": 0.0    # Sharpe between 0 and 0.5
    # Below 0 might be "NEGATIVE_RISK_ADJUSTED_RETURN" or similar
}

def calculate_expected_sharpe(price_series: pd.Series, annual_rf: float, annualization_factor: int) -> float:
    """Calculates the expected annualized Sharpe Ratio from a price series."""
    if len(price_series) < 2:
        return np.nan # Cannot calculate return with less than 2 points

    # Calculate daily returns
    returns = price_series.pct_change().dropna()

    if returns.empty:
        return np.nan

    # Calculate average daily return and standard deviation of daily return
    mean_daily_return = returns.mean()
    std_daily_return = returns.std()

    # Handle case of zero volatility
    if std_daily_return == 0:
        # Sharpe is infinite or undefined if volatility is 0, but practically
        # a high return with zero risk is excellent. Handle as per agent logic.
        # For this test, we assume non-zero std dev in generated data.
        # If std_daily_return could be 0, agent might return inf or a max value.
        # For now, let's assume test data avoids this.
        if mean_daily_return > 0:
             return np.inf # Or a large number indicating excellent performance
        else:
             return np.nan # Or 0 if 0 return, 0 volatility
             # Raise ValueError("Cannot calculate Sharpe with zero volatility and non-positive return")


    # Calculate daily risk-free rate
    # Approximation: annual_rf / annualization_factor
    # More precise: (1 + annual_rf)**(1/annualization_factor) - 1
    daily_rf = annual_rf / annualization_factor # Using approximation for simplicity matching common agent logic

    # Calculate daily Sharpe Ratio
    daily_sharpe = (mean_daily_return - daily_rf) / std_daily_return

    # Annualize the Sharpe Ratio
    annual_sharpe = daily_sharpe * np.sqrt(annualization_factor)

    return annual_sharpe

def determine_expected_verdict(sharpe_ratio: float, thresholds: dict) -> str:
    """Determines the expected verdict based on calculated Sharpe Ratio and thresholds."""
    # Sort thresholds by value descending to apply the highest threshold first
    sorted_thresholds = sorted(thresholds.items(), key=lambda item: item[1], reverse=True)

    for verdict, threshold_value in sorted_thresholds:
        if sharpe_ratio >= threshold_value:
            return verdict

    # Default verdict if below all thresholds (e.g., negative Sharpe)
    # Add a specific threshold for negative if needed, e.g., "NEGATIVE_RISK_ADJUSTED_RETURN": -np.inf
    return "POOR_RISK_ADJUSTED_RETURN" # Or adjust based on agent's logic

@pytest.mark.asyncio
@patch('backend.agents.decorators.get_tracker')
@patch('backend.agents.decorators.get_redis_client')
@patch('backend.agents.risk.sharpe_agent.fetch_price_series') # Patch where fetch_price_series is used
async def test_sharpe_agent_basic_positive(
    mock_fetch_prices,
    mock_get_redis,
    mock_get_tracker
):
    """
    Test Sharpe agent with data simulating a steady upward trend
    resulting in a positive Sharpe Ratio.
    """
    # --- Mock Configuration ---
    symbol = "TEST_SHARPE_POS"
    # Need slightly more than annualization factor + buffer for rolling calculations if any
    # But Sharpe is typically on the whole series after fetching
    num_periods = ANNUALIZATION_FACTOR + 10 # Enough data for a full year + buffer

    # Create price data simulating a steady upward trend
    # Example: roughly 15% annual return, relatively low volatility
    start_price = 100
    end_price = start_price * (1 + 0.15) # Target ~15% over a year
    prices = np.linspace(start_price, end_price, num_periods)
    # Add a little noise to ensure non-zero volatility
    prices = prices + np.random.normal(0, 0.5, num_periods) # Add some daily noise
    # Ensure prices are positive after adding noise
    prices = np.maximum(prices, 1.0)


    price_series = pd.Series(prices, index=pd.date_range(end=date.today(), periods=num_periods, freq='B')) # Business days

    # --- Calculate Expected Sharpe and Verdict ---
    expected_sharpe = calculate_expected_sharpe(price_series, ANNUAL_RISK_FREE_RATE, ANNUALIZATION_FACTOR)
    expected_verdict = determine_expected_verdict(expected_sharpe, SHARPE_THRESHOLDS)

    print(f"\n--- Data Verification for {symbol} ---")
    print(f"Generated {num_periods} prices from {price_series.index.min().date()} to {price_series.index.max().date()}")
    print(f"First Price: {price_series.iloc[0]:.2f}, Last Price: {price_series.iloc[-1]:.2f}")
    print(f"Expected Annualized Sharpe: {expected_sharpe:.2f}")
    print(f"Expected Verdict: {expected_verdict}")
    print("------------------------------------")

    # Basic check on expected value - should be positive with this data
    assert expected_sharpe > 0, f"Generated data unexpectedly resulted in non-positive Sharpe Ratio: {expected_sharpe}"


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

    # --- Run Agent ---
    result = await sharpe_run(symbol)

    # --- Assertions ---
    assert result is not None, "Agent should return a result dictionary"
    assert 'symbol' in result and result['symbol'] == symbol
    assert 'agent_name' in result and result['agent_name'] == agent_name
    assert 'verdict' in result
    assert 'confidence' in result
    assert 'value' in result # This should be the Sharpe Ratio
    assert 'details' in result
    assert 'sharpe_ratio' in result['details']

    assert result.get('error') is None, f"Agent returned error: {result.get('error')}"
    # Assert that the value and sharpe_ratio in details match the calculated expected value
    # Use pytest.approx for floating point comparison tolerance
    # Increase relative tolerance slightly
    assert pytest.approx(result['value'], rel=1e-3) == expected_sharpe, \
           f"Agent 'value' ({result['value']:.4f}) does not match expected Sharpe ({expected_sharpe:.4f})"
    assert pytest.approx(result['details']['sharpe_ratio'], rel=1e-3) == expected_sharpe, \
           f"Agent 'details.sharpe_ratio' ({result['details']['sharpe_ratio']:.4f}) does not match expected Sharpe ({expected_sharpe:.4f})"

    # Assert the expected verdict based on the calculated Sharpe
    assert result['verdict'] == expected_verdict, \
           f"Agent verdict ('{result['verdict']}') does not match expected verdict ('{expected_verdict}') for Sharpe Ratio {expected_sharpe:.2f}"

    # Assert confidence is within a reasonable range (e.g., 0 to 1)
    # The confidence calculation logic within the agent would determine the exact value
    # For now, a broad check might be sufficient if confidence isn't tied directly to Sharpe value in a simple way.
    assert 0 <= result['confidence'] <= 1, f"Agent confidence out of expected range (0-1): {result['confidence']}"


    # --- Verify Mocks ---
    mock_fetch_prices.assert_awaited_once_with(symbol)
    mock_get_redis.assert_awaited_once()
    mock_redis_instance.get.assert_awaited_once_with(f"{agent_name}:{symbol}")
    # Decorator should cache successful results
    if result.get('verdict') not in ['ERROR', 'NO_DATA']:
        # Check if set was called. The exact arguments to set depend on the decorator/agent's caching format.
        mock_redis_instance.set.assert_awaited_once()
    else:
        mock_redis_instance.set.assert_not_awaited()

    # Verify tracker was called via the decorator
    mock_get_tracker.assert_called_once() # Assumes get_tracker is called by the decorator once per agent run
    mock_tracker_instance.update_agent_status.assert_awaited_once()


@pytest.mark.asyncio
@patch('backend.agents.decorators.get_tracker')
@patch('backend.agents.decorators.get_redis_client')
@patch('backend.agents.risk.sharpe_agent.fetch_price_series')
async def test_sharpe_agent_insufficient_data(
    mock_fetch_prices,
    mock_get_redis,
    mock_get_tracker
):
    """
    Test Sharpe agent when insufficient data is available.
    Should return a NO_DATA verdict.
    """
    symbol = "TEST_SHARPE_NO_DATA"
    # Need at least 2 points for a return, but typically more for meaningful Sharpe
    # Let's test with 1 point, which should be clearly insufficient
    num_periods = 1

    prices = np.array([100.0])
    price_series = pd.Series(prices, index=pd.date_range(end=date.today(), periods=num_periods, freq='B'))

    mock_fetch_prices.return_value = price_series

    mock_redis_instance = AsyncMock()
    mock_redis_instance.get.return_value = None
    mock_redis_instance.set = AsyncMock()
    mock_get_redis.return_value = mock_redis_instance

    mock_tracker_instance = AsyncMock()
    mock_tracker_instance.update_agent_status = AsyncMock()
    mock_get_tracker.return_value = mock_tracker_instance

    # --- Run Agent ---
    result = await sharpe_run(symbol)

    # --- Assertions ---
    assert result is not None, "Agent should return a result dictionary"
    assert 'symbol' in result and result['symbol'] == symbol
    assert 'agent_name' in result and result['agent_name'] == agent_name
    assert 'verdict' in result

    # Should indicate lack of data
    assert result['verdict'] == "NO_DATA", f"Expected NO_DATA verdict, got {result['verdict']}"
    assert 'value' in result and result['value'] is None # Or 0, depends on agent's NO_DATA representation
    assert 'confidence' in result and result['confidence'] == 0.0 # Confidence should be low/zero
    assert 'details' in result # Details might contain an error message or indicate reason

    assert result.get('error') is None, f"Agent returned error: {result.get('error')}"


    # --- Verify Mocks ---
    mock_fetch_prices.assert_awaited_once_with(symbol)
    mock_get_redis.assert_awaited_once()
    mock_redis_instance.get.assert_awaited_once_with(f"{agent_name}:{symbol}")
    # NO_DATA results typically aren't cached, assert set was NOT called
    mock_redis_instance.set.assert_not_awaited()

    mock_get_tracker.assert_called_once()
    mock_tracker_instance.update_agent_status.assert_awaited_once()


# Optional: Add tests for other scenarios
# - Zero volatility (flat prices) - this could be tricky depending on agent's handling
# - Negative trend (resulting in negative Sharpe)
# - fetch_price_series returning None or empty DataFrame (similar to insufficient data)

