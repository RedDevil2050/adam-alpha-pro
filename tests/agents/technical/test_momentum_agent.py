import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, AsyncMock, MagicMock

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

# Sample data generation (remains the same)
SYMBOL = "TEST"
dates = pd.date_range(end=pd.Timestamp.today(), periods=300, freq='B') # ~1.2 years
np.random.seed(42)

def generate_prices(start_price, trend, volatility, length):
    prices = [start_price]
    for _ in range(1, length):
        daily_return = trend + np.random.normal(0, volatility)
        prices.append(prices[-1] * (1 + daily_return))
    # Ensure index matches the length requested
    return pd.Series(prices, index=dates[:length])


# Adjusted Scenarios based on previous analysis
prices_strong_positive = generate_prices(100, 0.002, 0.015, 300) # Strong upward trend (>15% avg)
prices_positive = generate_prices(100, 0.0005, 0.015, 300)      # Mild upward trend (0% < avg <= 15%)
prices_negative = generate_prices(100, -0.0005, 0.015, 300)     # Mild downward trend (-10% <= avg < 0%)
prices_strong_negative = generate_prices(100, -0.0015, 0.015, 300) # Strong downward trend (< -10% avg)
prices_flat = generate_prices(100, 0.00001, 0.005, 300)       # Very low trend, near zero
prices_insufficient = generate_prices(100, 0.001, 0.01, 100)      # Not enough data for 252 lookback

# --- Test Cases with Corrected Assertions ---

@pytest.mark.asyncio
@patch('backend.utils.cache_utils.get_redis_client', new_callable=AsyncMock)
@patch('backend.agents.technical.momentum_agent.fetch_historical_price_series', new_callable=AsyncMock)
@patch('backend.agents.technical.momentum_agent.get_settings')
async def test_momentum_strong_positive(mock_get_settings, mock_fetch_hist, mock_redis_client):
    # Arrange
    mock_settings_instance = MagicMock()
    mock_settings_instance.agent_settings.momentum.LOOKBACK_PERIODS = [21, 63, 126, 252]
    mock_settings_instance.agent_settings.momentum.THRESHOLD_STRONG_POSITIVE = 0.15
    mock_settings_instance.agent_settings.momentum.THRESHOLD_STRONG_NEGATIVE = -0.10
    mock_get_settings.return_value = mock_settings_instance

    mock_fetch_hist.return_value = prices_strong_positive
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get.return_value = None
    mock_redis_client.return_value = mock_redis_instance

    # Act
    result = await momentum_run(SYMBOL)

    # Assert
    assert result["symbol"] == SYMBOL
    assert result["agent_name"] == agent_name
    assert result["verdict"] == "STRONG_POSITIVE_MOMENTUM"
    assert result["value"] > (mock_settings_instance.agent_settings.momentum.THRESHOLD_STRONG_POSITIVE * 100)
    assert result["confidence"] == 0.8
    mock_fetch_hist.assert_awaited_once()
    # Use await_count for Redis mock assertions
    assert mock_redis_instance.get.await_count == 1
    assert mock_redis_instance.set.await_count == 1

@pytest.mark.asyncio
@patch('backend.utils.cache_utils.get_redis_client', new_callable=AsyncMock)
@patch('backend.agents.technical.momentum_agent.fetch_historical_price_series', new_callable=AsyncMock)
@patch('backend.agents.technical.momentum_agent.get_settings')
async def test_momentum_positive(mock_get_settings, mock_fetch_hist, mock_redis_client):
    # Arrange
    mock_settings_instance = MagicMock()
    mock_settings_instance.agent_settings.momentum.LOOKBACK_PERIODS = [21, 63, 126, 252]
    mock_settings_instance.agent_settings.momentum.THRESHOLD_STRONG_POSITIVE = 0.15
    mock_settings_instance.agent_settings.momentum.THRESHOLD_STRONG_NEGATIVE = -0.10
    mock_get_settings.return_value = mock_settings_instance

    mock_fetch_hist.return_value = prices_positive
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get.return_value = None
    mock_redis_client.return_value = mock_redis_instance

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
    assert mock_redis_instance.get.await_count == 1
    assert mock_redis_instance.set.await_count == 1

@pytest.mark.asyncio
@patch('backend.utils.cache_utils.get_redis_client', new_callable=AsyncMock)
@patch('backend.agents.technical.momentum_agent.fetch_historical_price_series', new_callable=AsyncMock)
@patch('backend.agents.technical.momentum_agent.get_settings')
async def test_momentum_negative(mock_get_settings, mock_fetch_hist, mock_redis_client):
    # Arrange
    mock_settings_instance = MagicMock()
    mock_settings_instance.agent_settings.momentum.LOOKBACK_PERIODS = [21, 63, 126, 252]
    mock_settings_instance.agent_settings.momentum.THRESHOLD_STRONG_POSITIVE = 0.15
    mock_settings_instance.agent_settings.momentum.THRESHOLD_STRONG_NEGATIVE = -0.10
    mock_get_settings.return_value = mock_settings_instance

    mock_fetch_hist.return_value = prices_negative
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get.return_value = None
    mock_redis_client.return_value = mock_redis_instance

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
    assert mock_redis_instance.get.await_count == 1
    assert mock_redis_instance.set.await_count == 1

@pytest.mark.asyncio
@patch('backend.utils.cache_utils.get_redis_client', new_callable=AsyncMock)
@patch('backend.agents.technical.momentum_agent.fetch_historical_price_series', new_callable=AsyncMock)
@patch('backend.agents.technical.momentum_agent.get_settings')
async def test_momentum_strong_negative(mock_get_settings, mock_fetch_hist, mock_redis_client):
    # Arrange
    mock_settings_instance = MagicMock()
    mock_settings_instance.agent_settings.momentum.LOOKBACK_PERIODS = [21, 63, 126, 252]
    mock_settings_instance.agent_settings.momentum.THRESHOLD_STRONG_POSITIVE = 0.15
    mock_settings_instance.agent_settings.momentum.THRESHOLD_STRONG_NEGATIVE = -0.10
    mock_get_settings.return_value = mock_settings_instance

    mock_fetch_hist.return_value = prices_strong_negative
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get.return_value = None
    mock_redis_client.return_value = mock_redis_instance

    # Act
    result = await momentum_run(SYMBOL)

    # Assert
    assert result["symbol"] == SYMBOL
    assert result["agent_name"] == agent_name
    assert result["verdict"] == "STRONG_NEGATIVE_MOMENTUM"
    assert result["value"] < (mock_settings_instance.agent_settings.momentum.THRESHOLD_STRONG_NEGATIVE * 100)
    assert result["confidence"] == 0.8 # Check exact confidence
    mock_fetch_hist.assert_awaited_once()
    assert mock_redis_instance.get.await_count == 1
    assert mock_redis_instance.set.await_count == 1

@pytest.mark.asyncio
@patch('backend.utils.cache_utils.get_redis_client', new_callable=AsyncMock)
@patch('backend.agents.technical.momentum_agent.fetch_historical_price_series', new_callable=AsyncMock)
@patch('backend.agents.technical.momentum_agent.get_settings')
async def test_momentum_flat(mock_get_settings, mock_fetch_hist, mock_redis_client):
    # Arrange
    mock_settings_instance = MagicMock()
    mock_settings_instance.agent_settings.momentum.LOOKBACK_PERIODS = [21, 63, 126, 252]
    mock_settings_instance.agent_settings.momentum.THRESHOLD_STRONG_POSITIVE = 0.15
    mock_settings_instance.agent_settings.momentum.THRESHOLD_STRONG_NEGATIVE = -0.10
    mock_get_settings.return_value = mock_settings_instance

    mock_fetch_hist.return_value = prices_flat
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get.return_value = None
    mock_redis_client.return_value = mock_redis_instance

    # Act
    result = await momentum_run(SYMBOL)

    # Assert
    assert result["symbol"] == SYMBOL
    assert result["agent_name"] == agent_name
    assert result["verdict"] == "NEUTRAL_MOMENTUM"
    neutral_tolerance_pct = 1e-4 * 100
    assert result["value"] == pytest.approx(0.0, abs=neutral_tolerance_pct)
    assert result["confidence"] == 0.4
    mock_fetch_hist.assert_awaited_once()
    assert mock_redis_instance.get.await_count == 1
    assert mock_redis_instance.set.await_count == 1

@pytest.mark.asyncio
@patch('backend.utils.cache_utils.get_redis_client', new_callable=AsyncMock)
@patch('backend.agents.technical.momentum_agent.fetch_historical_price_series', new_callable=AsyncMock)
@patch('backend.agents.technical.momentum_agent.get_settings')
async def test_momentum_insufficient_data(mock_get_settings, mock_fetch_hist, mock_redis_client):
    # Arrange
    mock_settings_instance = MagicMock()
    mock_settings_instance.agent_settings.momentum.LOOKBACK_PERIODS = [21, 63, 126, 252]
    mock_get_settings.return_value = mock_settings_instance

    mock_fetch_hist.return_value = prices_insufficient # Less data than max lookback
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get.return_value = None
    mock_redis_client.return_value = mock_redis_instance

    # Act
    result = await momentum_run(SYMBOL)

    # Assert
    assert result["symbol"] == SYMBOL
    assert result["agent_name"] == agent_name
    assert result["verdict"] == "NO_DATA"
    assert result["value"] is None
    assert result["confidence"] == 0.0
    assert "Insufficient data" in result["details"]["reason"]
    mock_fetch_hist.assert_awaited_once()
    assert mock_redis_instance.get.await_count == 1
    assert mock_redis_instance.set.await_count == 0 # Correct assertion for no set

@pytest.mark.asyncio
@patch('backend.utils.cache_utils.get_redis_client', new_callable=AsyncMock)
@patch('backend.agents.technical.momentum_agent.fetch_historical_price_series', new_callable=AsyncMock)
@patch('backend.agents.technical.momentum_agent.get_settings')
async def test_momentum_fetch_error(mock_get_settings, mock_fetch_hist, mock_redis_client):
    # Arrange
    mock_settings_instance = MagicMock()
    mock_settings_instance.agent_settings.momentum.LOOKBACK_PERIODS = [21, 63, 126, 252]
    mock_get_settings.return_value = mock_settings_instance

    error_message = "API Error"
    mock_fetch_hist.side_effect = Exception(error_message)
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get.return_value = None
    mock_redis_client.return_value = mock_redis_instance

    # Act
    result = await momentum_run(SYMBOL)

    # Assert
    assert result["symbol"] == SYMBOL
    assert result["agent_name"] == agent_name
    assert result["verdict"] == "ERROR"
    assert result["value"] is None
    assert result["confidence"] == 0.0
    assert error_message in result["error"]
    mock_fetch_hist.assert_awaited_once()
    assert mock_redis_instance.get.await_count == 1
    assert mock_redis_instance.set.await_count == 0 # Correct assertion for no set

