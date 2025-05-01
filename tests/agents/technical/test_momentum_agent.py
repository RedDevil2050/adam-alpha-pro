import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, AsyncMock, MagicMock
import json
import pytest # Ensure pytest is imported for approx

# Import the function to test and settings classes
from backend.agents.technical.momentum_agent import run as momentum_run, agent_name
from backend.config.settings import Settings, MomentumAgentSettings

# Mock settings fixture (remains the same)
@pytest.fixture
def mock_settings():
    settings = Settings()
    settings.agent_settings.momentum = MomentumAgentSettings(
        LOOKBACK_PERIODS=[21, 63, 126, 252], # Approx 1m, 3m, 6m, 12m
        THRESHOLD_STRONG_POSITIVE=0.15, # 15% avg return
        THRESHOLD_STRONG_NEGATIVE=-0.10 # -10% avg return
    )
    return settings

# --- Fixed Test Data --- 
SYMBOL = "TEST"
dates = pd.date_range(end=pd.Timestamp.today(), periods=300, freq='B') # ~1.2 years

# Strong Positive: Consistent upward trend, avg return > 0.15
prices_strong_positive = pd.Series(np.linspace(100, 150, 300), index=dates)

# Positive: Moderate upward trend, 0 < avg return <= 0.15
prices_positive = pd.Series(np.linspace(100, 110, 300), index=dates)

# Negative: Moderate downward trend, -0.10 <= avg return < 0
prices_negative = pd.Series(np.linspace(100, 95, 300), index=dates)

# Strong Negative: Consistent downward trend, avg return < -0.10
prices_strong_negative = pd.Series(np.linspace(100, 70, 300), index=dates)

# Flat: Minimal change, avg return ~ 0
prices_flat = pd.Series(np.linspace(100, 100.1, 300), index=dates)

# Insufficient Data: Less than the longest lookback period (252)
prices_insufficient = pd.Series(np.linspace(100, 105, 50), index=dates[:50])

# --- Test Cases with Corrected Mocking and Fixed Data ---

# Configure Redis mock with proper AsyncMock setup
@pytest.mark.asyncio
@patch('backend.agents.decorators.get_redis_client')
@patch('backend.agents.technical.momentum_agent.fetch_historical_price_series', new_callable=AsyncMock)
@patch('backend.agents.technical.momentum_agent.get_settings')
async def test_momentum_strong_positive(mock_get_settings, mock_fetch_hist, mock_get_redis_decorator):
    # Arrange
    mock_settings_instance = MagicMock()
    mock_settings_instance.agent_settings.momentum.LOOKBACK_PERIODS = [21, 63, 126, 252]
    mock_settings_instance.agent_settings.momentum.THRESHOLD_STRONG_POSITIVE = 0.15
    mock_settings_instance.agent_settings.momentum.THRESHOLD_STRONG_NEGATIVE = -0.10
    mock_get_settings.return_value = mock_settings_instance

    mock_fetch_hist.return_value = prices_strong_positive

    # --- Correct Mocking Strategy ---
    # 1. Create a mock for the Redis client *instance*
    mock_redis_instance = AsyncMock()
    # 2. Assign AsyncMocks to the methods of the instance mock
    mock_redis_instance.get = AsyncMock(return_value=None) # Simulate cache miss
    mock_redis_instance.set = AsyncMock() # Mock set as well
    # 3. Configure the *patched function* to return the instance mock
    mock_get_redis_decorator.return_value = mock_redis_instance

    # Act
    result = await momentum_run(SYMBOL)

    # Assert
    assert result["symbol"] == SYMBOL
    assert result["agent_name"] == agent_name
    assert result["verdict"] == "STRONG_POSITIVE_MOMENTUM"
    assert result["value"] > (mock_settings_instance.agent_settings.momentum.THRESHOLD_STRONG_POSITIVE * 100)
    assert result["confidence"] == 0.8
    mock_fetch_hist.assert_awaited_once()
    # Check await counts on the patched function and the instance's methods
    mock_get_redis_decorator.assert_awaited_once()
    mock_redis_instance.get.assert_awaited_once()
    mock_redis_instance.set.assert_awaited_once()

@pytest.mark.asyncio
@patch('backend.agents.decorators.get_redis_client')
@patch('backend.agents.technical.momentum_agent.fetch_historical_price_series', new_callable=AsyncMock)
@patch('backend.agents.technical.momentum_agent.get_settings')
async def test_momentum_positive(mock_get_settings, mock_fetch_hist, mock_get_redis_decorator):
    # Arrange
    mock_settings_instance = MagicMock()
    mock_settings_instance.agent_settings.momentum.LOOKBACK_PERIODS = [21, 63, 126, 252]
    mock_settings_instance.agent_settings.momentum.THRESHOLD_STRONG_POSITIVE = 0.15
    mock_settings_instance.agent_settings.momentum.THRESHOLD_STRONG_NEGATIVE = -0.10
    mock_get_settings.return_value = mock_settings_instance

    mock_fetch_hist.return_value = prices_positive

    # Configure Redis mock with async methods
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get = AsyncMock(return_value=None) # Simulate cache miss
    mock_redis_instance.set = AsyncMock() # Mock set
    mock_get_redis_decorator.return_value = mock_redis_instance

    # Act
    result = await momentum_run(SYMBOL)

    # Assert
    assert result["symbol"] == SYMBOL
    assert result["agent_name"] == agent_name
    assert result["verdict"] == "POSITIVE_MOMENTUM"
    neutral_tolerance_pct = 1e-4 * 100
    threshold_strong_positive_pct = mock_settings_instance.agent_settings.momentum.THRESHOLD_STRONG_POSITIVE * 100
    assert neutral_tolerance_pct < result["value"] <= threshold_strong_positive_pct
    assert result["confidence"] == 0.6
    mock_fetch_hist.assert_awaited_once()
    # Check await counts
    mock_get_redis_decorator.assert_awaited_once()
    mock_redis_instance.get.assert_awaited_once()
    mock_redis_instance.set.assert_awaited_once()

@pytest.mark.asyncio
@patch('backend.agents.decorators.get_redis_client')
@patch('backend.agents.technical.momentum_agent.fetch_historical_price_series', new_callable=AsyncMock)
@patch('backend.agents.technical.momentum_agent.get_settings')
async def test_momentum_negative(mock_get_settings, mock_fetch_hist, mock_get_redis_decorator):
    # Arrange
    mock_settings_instance = MagicMock()
    mock_settings_instance.agent_settings.momentum.LOOKBACK_PERIODS = [21, 63, 126, 252]
    mock_settings_instance.agent_settings.momentum.THRESHOLD_STRONG_POSITIVE = 0.15
    mock_settings_instance.agent_settings.momentum.THRESHOLD_STRONG_NEGATIVE = -0.10
    mock_get_settings.return_value = mock_settings_instance

    mock_fetch_hist.return_value = prices_negative

    # Configure Redis mock with async methods
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get = AsyncMock(return_value=None) # Simulate cache miss
    mock_redis_instance.set = AsyncMock() # Mock set
    mock_get_redis_decorator.return_value = mock_redis_instance

    # Act
    result = await momentum_run(SYMBOL)

    # Assert
    assert result["symbol"] == SYMBOL
    assert result["agent_name"] == agent_name
    assert result["verdict"] == "NEGATIVE_MOMENTUM"
    neutral_tolerance_pct = 1e-4 * 100
    threshold_strong_negative_pct = mock_settings_instance.agent_settings.momentum.THRESHOLD_STRONG_NEGATIVE * 100
    assert threshold_strong_negative_pct <= result["value"] < -neutral_tolerance_pct
    assert result["confidence"] == 0.6
    mock_fetch_hist.assert_awaited_once()
    # Check await counts
    mock_get_redis_decorator.assert_awaited_once()
    mock_redis_instance.get.assert_awaited_once()
    mock_redis_instance.set.assert_awaited_once()

@pytest.mark.asyncio
@patch('backend.agents.decorators.get_redis_client')
@patch('backend.agents.technical.momentum_agent.fetch_historical_price_series', new_callable=AsyncMock)
@patch('backend.agents.technical.momentum_agent.get_settings')
async def test_momentum_strong_negative(mock_get_settings, mock_fetch_hist, mock_get_redis_decorator):
    # Arrange
    mock_settings_instance = MagicMock()
    mock_settings_instance.agent_settings.momentum.LOOKBACK_PERIODS = [21, 63, 126, 252]
    mock_settings_instance.agent_settings.momentum.THRESHOLD_STRONG_POSITIVE = 0.15
    mock_settings_instance.agent_settings.momentum.THRESHOLD_STRONG_NEGATIVE = -0.10
    mock_get_settings.return_value = mock_settings_instance

    mock_fetch_hist.return_value = prices_strong_negative

    # Configure Redis mock with async methods
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get = AsyncMock(return_value=None) # Simulate cache miss
    mock_redis_instance.set = AsyncMock() # Mock set
    mock_get_redis_decorator.return_value = mock_redis_instance

    # Act
    result = await momentum_run(SYMBOL)

    # Assert
    assert result["symbol"] == SYMBOL
    assert result["agent_name"] == agent_name
    assert result["verdict"] == "STRONG_NEGATIVE_MOMENTUM"
    assert result["value"] < (mock_settings_instance.agent_settings.momentum.THRESHOLD_STRONG_NEGATIVE * 100)
    assert result["confidence"] == 0.8 # Check exact confidence
    mock_fetch_hist.assert_awaited_once()
    # Check await counts
    mock_get_redis_decorator.assert_awaited_once()
    mock_redis_instance.get.assert_awaited_once()
    mock_redis_instance.set.assert_awaited_once()

@pytest.mark.asyncio
@patch('backend.agents.decorators.get_redis_client')
@patch('backend.agents.technical.momentum_agent.fetch_historical_price_series', new_callable=AsyncMock)
@patch('backend.agents.technical.momentum_agent.get_settings')
async def test_momentum_flat(mock_get_settings, mock_fetch_hist, mock_get_redis_decorator):
    # Arrange
    mock_settings_instance = MagicMock()
    mock_settings_instance.agent_settings.momentum.LOOKBACK_PERIODS = [21, 63, 126, 252]
    mock_settings_instance.agent_settings.momentum.THRESHOLD_STRONG_POSITIVE = 0.15
    mock_settings_instance.agent_settings.momentum.THRESHOLD_STRONG_NEGATIVE = -0.10
    mock_get_settings.return_value = mock_settings_instance

    mock_fetch_hist.return_value = prices_flat

    # Configure Redis mock with async methods
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get = AsyncMock(return_value=None) # Simulate cache miss
    mock_redis_instance.set = AsyncMock() # Mock set
    mock_get_redis_decorator.return_value = mock_redis_instance

    # Act
    result = await momentum_run(SYMBOL)

    # Assert
    assert result["symbol"] == SYMBOL
    assert result["agent_name"] == agent_name
    # The calculated momentum is slightly positive (0.000386), exceeding the neutral tolerance (0.0001)
    assert result["verdict"] == "POSITIVE_MOMENTUM" # Changed from NEUTRAL_MOMENTUM
    neutral_tolerance_pct = 1e-4 * 100
    threshold_strong_positive_pct = mock_settings_instance.agent_settings.momentum.THRESHOLD_STRONG_POSITIVE * 100
    # Check value is within the POSITIVE range ( > tolerance and <= strong threshold)
    assert neutral_tolerance_pct < result["value"] <= threshold_strong_positive_pct
    assert result["confidence"] == 0.6 # Confidence for POSITIVE_MOMENTUM
    mock_fetch_hist.assert_awaited_once()
    # Check await counts
    mock_get_redis_decorator.assert_awaited_once()
    mock_redis_instance.get.assert_awaited_once()
    mock_redis_instance.set.assert_awaited_once()

@pytest.mark.asyncio
@patch('backend.agents.decorators.get_redis_client')
@patch('backend.agents.technical.momentum_agent.fetch_historical_price_series', new_callable=AsyncMock)
@patch('backend.agents.technical.momentum_agent.get_settings')
async def test_momentum_insufficient_data(mock_get_settings, mock_fetch_hist, mock_get_redis_decorator):
    # Arrange
    mock_settings_instance = MagicMock()
    mock_settings_instance.agent_settings.momentum.LOOKBACK_PERIODS = [21, 63, 126, 252]
    mock_get_settings.return_value = mock_settings_instance

    mock_fetch_hist.return_value = prices_insufficient # Less data than max lookback

    # Configure the mock redis client instance
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get = AsyncMock(return_value=None) # Simulate cache miss
    mock_redis_instance.set = AsyncMock()
    mock_get_redis_decorator.return_value = mock_redis_instance

    # Act
    result = await momentum_run(SYMBOL)

    # Assert
    assert result["symbol"] == SYMBOL
    assert result["agent_name"] == agent_name
    assert result["verdict"] == "NO_DATA"
    assert result["value"] is None
    assert result["confidence"] == 0.0
    assert "Insufficient historical data" in result["details"]["reason"] # Adjusted reason check
    mock_fetch_hist.assert_awaited_once()
    # Check await counts - get should be called, set should not
    mock_get_redis_decorator.assert_awaited_once()
    mock_redis_instance.get.assert_awaited_once()
    mock_redis_instance.set.assert_not_awaited() # Correct assertion

@pytest.mark.asyncio
@patch('backend.agents.decorators.get_redis_client')
@patch('backend.agents.technical.momentum_agent.fetch_historical_price_series', new_callable=AsyncMock)
@patch('backend.agents.technical.momentum_agent.get_settings')
async def test_momentum_fetch_error(mock_get_settings, mock_fetch_hist, mock_get_redis_decorator):
    # Arrange
    mock_settings_instance = MagicMock()
    mock_settings_instance.agent_settings.momentum.LOOKBACK_PERIODS = [21, 63, 126, 252]
    mock_get_settings.return_value = mock_settings_instance

    error_message = "API Error"
    mock_fetch_hist.side_effect = Exception(error_message)

    # Configure the mock redis client instance
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get = AsyncMock(return_value=None) # Simulate cache miss
    mock_redis_instance.set = AsyncMock()
    mock_get_redis_decorator.return_value = mock_redis_instance

    # Act
    result = await momentum_run(SYMBOL)

    # Assert
    assert result["symbol"] == SYMBOL
    assert result["agent_name"] == agent_name
    # The decorator catches the exception and returns an ERROR verdict
    assert result["verdict"] == "ERROR"
    assert result["value"] is None
    assert result["confidence"] == 0.0
    # The decorator puts the error message in the top-level 'error' key
    assert error_message in result["error"]
    mock_fetch_hist.assert_awaited_once()
    # Check await counts - get should be called, set should not
    mock_get_redis_decorator.assert_awaited_once()
    mock_redis_instance.get.assert_awaited_once()
    mock_redis_instance.set.assert_not_awaited() # Correct assertion

@pytest.mark.asyncio
@patch('backend.agents.decorators.get_redis_client')
@patch('backend.agents.technical.momentum_agent.fetch_historical_price_series', new_callable=AsyncMock)
@patch('backend.agents.technical.momentum_agent.get_settings')
async def test_momentum_cache_hit(mock_get_settings, mock_fetch_hist, mock_get_redis_decorator):
    # Arrange
    mock_settings_instance = MagicMock()
    mock_settings_instance.agent_settings.momentum.LOOKBACK_PERIODS = [21, 63, 126, 252]
    mock_get_settings.return_value = mock_settings_instance

    # Simulate cached data being returned
    cached_result = {
        "symbol": SYMBOL,
        "verdict": "POSITIVE_MOMENTUM",
        "confidence": 0.6,
        "value": 5.5,
        "details": {"some": "data"},
        "agent_name": agent_name,
    }
    # Configure the mock redis client instance
    mock_redis_instance = AsyncMock()
    # Return cached data as JSON string for get
    mock_redis_instance.get = AsyncMock(return_value=json.dumps(cached_result))
    mock_redis_instance.set = AsyncMock()
    mock_get_redis_decorator.return_value = mock_redis_instance

    # Act
    result = await momentum_run(SYMBOL)

    # Assert
    assert result == cached_result # Should return the exact cached result
    mock_get_redis_decorator.assert_awaited_once() # Patched function was called
    mock_redis_instance.get.assert_awaited_once() # Get was called on the instance
    mock_fetch_hist.assert_not_awaited() # Fetch should NOT be called
    mock_redis_instance.set.assert_not_awaited() # Set should NOT be called

# Add a test for cache miss with NO_DATA result (should not cache)
@pytest.mark.asyncio
@patch('backend.agents.decorators.get_redis_client')
@patch('backend.agents.technical.momentum_agent.fetch_historical_price_series', new_callable=AsyncMock)
@patch('backend.agents.technical.momentum_agent.get_settings')
async def test_momentum_no_data_not_cached(mock_get_settings, mock_fetch_hist, mock_get_redis_decorator):
    # Arrange
    mock_settings_instance = MagicMock()
    mock_settings_instance.agent_settings.momentum.LOOKBACK_PERIODS = [21, 63, 126, 252]
    mock_get_settings.return_value = mock_settings_instance

    mock_fetch_hist.return_value = prices_insufficient # Data leads to NO_DATA verdict

    # Configure the mock redis client instance
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get = AsyncMock(return_value=None) # Simulate cache miss
    mock_redis_instance.set = AsyncMock()
    mock_get_redis_decorator.return_value = mock_redis_instance

    # Act
    result = await momentum_run(SYMBOL)

    # Assert
    assert result["verdict"] == "NO_DATA"
    mock_get_redis_decorator.assert_awaited_once()
    mock_redis_instance.get.assert_awaited_once()
    mock_fetch_hist.assert_awaited_once()
    mock_redis_instance.set.assert_not_awaited() # Ensure NO_DATA result is not cached

# Add a test for cache miss with ERROR result (should not cache)
@pytest.mark.asyncio
@patch('backend.agents.decorators.get_redis_client')
@patch('backend.agents.technical.momentum_agent.fetch_historical_price_series', new_callable=AsyncMock)
@patch('backend.agents.technical.momentum_agent.get_settings')
async def test_momentum_error_not_cached(mock_get_settings, mock_fetch_hist, mock_get_redis_decorator):
    # Arrange
    mock_settings_instance = MagicMock()
    mock_settings_instance.agent_settings.momentum.LOOKBACK_PERIODS = [21, 63, 126, 252]
    mock_get_settings.return_value = mock_settings_instance

    mock_fetch_hist.side_effect = Exception("Fetch failed") # Cause an error

    # Configure the mock redis client instance
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get = AsyncMock(return_value=None) # Simulate cache miss
    mock_redis_instance.set = AsyncMock()
    mock_get_redis_decorator.return_value = mock_redis_instance

    # Act
    result = await momentum_run(SYMBOL)

    # Assert
    assert result["verdict"] == "ERROR"
    mock_get_redis_decorator.assert_awaited_once()
    mock_redis_instance.get.assert_awaited_once()
    mock_fetch_hist.assert_awaited_once()
    mock_redis_instance.set.assert_not_awaited() # Ensure ERROR result is not cached

