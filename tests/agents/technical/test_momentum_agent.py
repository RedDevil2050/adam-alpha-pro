import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, AsyncMock, MagicMock

# Import the function to test and settings classes
from backend.agents.technical.momentum_agent import run as momentum_run, agent_name
from backend.config.settings import Settings, MomentumAgentSettings

# Mock settings
@pytest.fixture
def mock_settings():
    settings = Settings()
    settings.agent_settings.momentum = MomentumAgentSettings(
        LOOKBACK_PERIODS=[21, 63, 126, 252], # Approx 1m, 3m, 6m, 12m
        THRESHOLD_STRONG_POSITIVE=0.15, # 15% avg return
        THRESHOLD_STRONG_NEGATIVE=-0.10 # -10% avg return
    )
    return settings

# Sample data
SYMBOL = "TEST"
# Generate historical data (more than 1 year needed)
dates = pd.date_range(end=pd.Timestamp.today(), periods=300, freq='B') # ~1.2 years
np.random.seed(42)

def generate_prices(start_price, trend, volatility, length):
    prices = [start_price]
    for _ in range(1, length):
        daily_return = trend + np.random.normal(0, volatility)
        prices.append(prices[-1] * (1 + daily_return))
    # Ensure index matches the length requested
    return pd.Series(prices, index=dates[:length])


# Scenarios
prices_strong_positive = generate_prices(100, 0.0015, 0.015, 300) # Strong upward trend
prices_positive = generate_prices(100, 0.0005, 0.015, 300)      # Mild upward trend
prices_negative = generate_prices(100, -0.0003, 0.015, 300)     # Mild downward trend
prices_strong_negative = generate_prices(100, -0.0010, 0.015, 300) # Strong downward trend
prices_insufficient = generate_prices(100, 0.001, 0.01, 100)      # Not enough data for 252 lookback
prices_flat = generate_prices(100, 0.0, 0.0001, 300)              # Flat price series

@pytest.mark.asyncio
@patch('backend.utils.cache_utils.get_redis_client', new_callable=AsyncMock) # 1st patch
@patch('backend.agents.technical.momentum_agent.fetch_historical_price_series', new_callable=AsyncMock) # 2nd patch
@patch('backend.agents.technical.momentum_agent.get_settings') # 3rd patch
async def test_momentum_strong_positive(mock_get_settings, mock_fetch_hist, mock_redis_client): # Corrected order
    # Arrange
    # Configure the mock settings object
    mock_settings_instance = MagicMock()
    mock_settings_instance.agent_settings.momentum.LOOKBACK_PERIODS = [21, 63, 126, 252]
    mock_get_settings.return_value = mock_settings_instance

    mock_fetch_hist.return_value = prices_strong_positive
    mock_redis_client.get.return_value = None
    # Act
    result = await momentum_run(SYMBOL)
    # Assert
    assert result["symbol"] == SYMBOL
    assert result["agent_name"] == agent_name
    assert result["verdict"] == "STRONG_POSITIVE_MOMENTUM"
    assert result["value"] > mock_settings_instance.agent_settings.momentum.THRESHOLD_STRONG_POSITIVE
    assert result["confidence"] > 0.7 # Example confidence check
    assert "average_return" in result["details"]
    mock_fetch_hist.assert_awaited_once()
    mock_redis_client.get.assert_awaited_once_with(f"{agent_name}:{SYMBOL}")

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
    mock_redis_client.get.return_value = None
    # Act
    result = await momentum_run(SYMBOL)
    # Assert
    assert result["symbol"] == SYMBOL
    assert result["agent_name"] == agent_name
    assert result["verdict"] == "POSITIVE_MOMENTUM"
    assert 0 < result["value"] <= mock_settings_instance.agent_settings.momentum.THRESHOLD_STRONG_POSITIVE
    assert result["confidence"] > 0.5
    mock_fetch_hist.assert_awaited_once()
    mock_redis_client.get.assert_awaited_once_with(f"{agent_name}:{SYMBOL}")

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
    mock_redis_client.get.return_value = None
    # Act
    result = await momentum_run(SYMBOL)
    # Assert
    assert result["symbol"] == SYMBOL
    assert result["agent_name"] == agent_name
    assert result["verdict"] == "NEGATIVE_MOMENTUM"
    assert mock_settings_instance.agent_settings.momentum.THRESHOLD_STRONG_NEGATIVE <= result["value"] < 0
    assert result["confidence"] > 0.5
    mock_fetch_hist.assert_awaited_once()
    mock_redis_client.get.assert_awaited_once_with(f"{agent_name}:{SYMBOL}")

@pytest.mark.asyncio
@patch('backend.utils.cache_utils.get_redis_client', new_callable=AsyncMock)
@patch('backend.agents.technical.momentum_agent.fetch_historical_price_series', new_callable=AsyncMock)
@patch('backend.agents.technical.momentum_agent.get_settings')
async def test_momentum_strong_negative(mock_get_settings, mock_fetch_hist, mock_redis_client):
    # Arrange
    mock_settings_instance = MagicMock()
    mock_settings_instance.agent_settings.momentum.LOOKBACK_PERIODS = [21, 63, 126, 252]
    mock_settings_instance.agent_settings.momentum.THRESHOLD_STRONG_NEGATIVE = -0.10
    mock_get_settings.return_value = mock_settings_instance

    mock_fetch_hist.return_value = prices_strong_negative
    mock_redis_client.get.return_value = None
    # Act
    result = await momentum_run(SYMBOL)
    # Assert
    assert result["symbol"] == SYMBOL
    assert result["agent_name"] == agent_name
    assert result["verdict"] == "STRONG_NEGATIVE_MOMENTUM"
    assert result["value"] < mock_settings_instance.agent_settings.momentum.THRESHOLD_STRONG_NEGATIVE
    assert result["confidence"] > 0.7
    mock_fetch_hist.assert_awaited_once()
    mock_redis_client.get.assert_awaited_once_with(f"{agent_name}:{SYMBOL}")

@pytest.mark.asyncio
@patch('backend.utils.cache_utils.get_redis_client', new_callable=AsyncMock)
@patch('backend.agents.technical.momentum_agent.fetch_historical_price_series', new_callable=AsyncMock)
@patch('backend.agents.technical.momentum_agent.get_settings')
async def test_momentum_flat(mock_get_settings, mock_fetch_hist, mock_redis_client):
    # Arrange
    mock_settings_instance = MagicMock()
    mock_settings_instance.agent_settings.momentum.LOOKBACK_PERIODS = [21, 63, 126, 252]
    mock_settings_instance.agent_settings.momentum.THRESHOLD_STRONG_NEGATIVE = -0.10 # Needed for range
    mock_get_settings.return_value = mock_settings_instance

    mock_fetch_hist.return_value = prices_flat
    mock_redis_client.get.return_value = None
    # Act
    result = await momentum_run(SYMBOL)
    # Assert
    assert result["symbol"] == SYMBOL
    assert result["agent_name"] == agent_name
    assert result["verdict"] == "NEUTRAL_MOMENTUM"
    neutral_tolerance = 1e-4
    assert -neutral_tolerance <= (result["value"] / 100) <= neutral_tolerance
    assert result["confidence"] == 0.4
    mock_fetch_hist.assert_awaited_once()
    mock_redis_client.get.assert_awaited_once_with(f"{agent_name}:{SYMBOL}")

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
    mock_redis_client.get.return_value = None
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
    mock_redis_client.get.assert_awaited_once_with(f"{agent_name}:{SYMBOL}")

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
    mock_redis_client.get.return_value = None
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
    mock_redis_client.get.assert_awaited_once_with(f"{agent_name}:{SYMBOL}")

