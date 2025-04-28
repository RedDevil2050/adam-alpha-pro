import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

import pytest
import asyncio
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock, AsyncMock

# Import the function to test and settings classes
from backend.agents.technical.momentum_agent import run as momentum_run, agent_name
from backend.config.settings import Settings, AgentSettings, MomentumAgentSettings

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

@pytest.mark.asyncio
@patch('redis.asyncio.client.Redis', new_callable=AsyncMock)
@patch('backend.agents.technical.momentum_agent.get_settings')
@patch('backend.agents.technical.momentum_agent.fetch_historical_price_series', new_callable=AsyncMock)
async def test_momentum_strong_positive(mock_fetch_hist, mock_get_settings, mock_redis, mock_settings):
    # Arrange
    mock_get_settings.return_value = mock_settings
    mock_fetch_hist.return_value = prices_strong_positive
    mock_redis.get.return_value = None
    # Act
    result = await momentum_run(SYMBOL)
    # Assert
    assert result["symbol"] == SYMBOL
    assert result["agent_name"] == agent_name
    assert result["verdict"] == "STRONG_POSITIVE_MOMENTUM"
    assert result["confidence"] == 0.7
    assert result["value"] > mock_settings.agent_settings.momentum.THRESHOLD_STRONG_POSITIVE * 100
    assert result["details"]["average_momentum_pct"] == result["value"]
    assert "return_21d_pct" in result["details"]
    assert "return_63d_pct" in result["details"]
    assert "return_126d_pct" in result["details"]
    assert "return_252d_pct" in result["details"]
    assert result["details"]["config_used"]["lookback_periods"] == mock_settings.agent_settings.momentum.LOOKBACK_PERIODS

@pytest.mark.asyncio
@patch('redis.asyncio.client.Redis', new_callable=AsyncMock)
@patch('backend.agents.technical.momentum_agent.get_settings')
@patch('backend.agents.technical.momentum_agent.fetch_historical_price_series', new_callable=AsyncMock)
async def test_momentum_positive(mock_fetch_hist, mock_get_settings, mock_redis, mock_settings):
    # Arrange
    mock_get_settings.return_value = mock_settings
    mock_fetch_hist.return_value = prices_positive
    mock_redis.get.return_value = None

    # Act
    result = await momentum_run(SYMBOL)

    # Assert
    assert result["symbol"] == SYMBOL
    assert result["agent_name"] == agent_name
    assert result["verdict"] == "POSITIVE_MOMENTUM"
    assert result["confidence"] == 0.5
    assert 0 < result["value"] <= mock_settings.agent_settings.momentum.THRESHOLD_STRONG_POSITIVE * 100

@pytest.mark.asyncio
@patch('redis.asyncio.client.Redis', new_callable=AsyncMock)
@patch('backend.agents.technical.momentum_agent.get_settings')
@patch('backend.agents.technical.momentum_agent.fetch_historical_price_series', new_callable=AsyncMock)
async def test_momentum_negative(mock_fetch_hist, mock_get_settings, mock_redis, mock_settings):
    # Arrange
    mock_get_settings.return_value = mock_settings
    mock_fetch_hist.return_value = prices_negative
    mock_redis.get.return_value = None

    # Act
    result = await momentum_run(SYMBOL)

    # Assert
    assert result["symbol"] == SYMBOL
    assert result["agent_name"] == agent_name
    assert result["verdict"] == "NEGATIVE_MOMENTUM"
    assert result["confidence"] == 0.5
    assert mock_settings.agent_settings.momentum.THRESHOLD_STRONG_NEGATIVE * 100 <= result["value"] < 0

@pytest.mark.asyncio
@patch('redis.asyncio.client.Redis', new_callable=AsyncMock)
@patch('backend.agents.technical.momentum_agent.get_settings')
@patch('backend.agents.technical.momentum_agent.fetch_historical_price_series', new_callable=AsyncMock)
async def test_momentum_strong_negative(mock_fetch_hist, mock_get_settings, mock_redis, mock_settings):
    # Arrange
    mock_get_settings.return_value = mock_settings
    mock_fetch_hist.return_value = prices_strong_negative
    mock_redis.get.return_value = None

    # Act
    result = await momentum_run(SYMBOL)

    # Assert
    assert result["symbol"] == SYMBOL
    assert result["agent_name"] == agent_name
    assert result["verdict"] == "STRONG_NEGATIVE_MOMENTUM"
    assert result["confidence"] == 0.7
    assert result["value"] < mock_settings.agent_settings.momentum.THRESHOLD_STRONG_NEGATIVE * 100

@pytest.mark.asyncio
@patch('backend.agents.technical.momentum_agent.get_settings')
@patch('backend.agents.technical.momentum_agent.fetch_historical_price_series', new_callable=AsyncMock)
async def test_momentum_no_data_insufficient_history(mock_fetch_hist, mock_get_settings, mock_settings):
    # Arrange
    mock_get_settings.return_value = mock_settings
    mock_fetch_hist.return_value = prices_insufficient # Only 100 data points
    mock_redis.get.return_value = None

    # Act
    result = await momentum_run(SYMBOL)

    # Assert
    assert result["symbol"] == SYMBOL
    assert result["agent_name"] == agent_name
    assert result["verdict"] == "NO_DATA"
    assert result["confidence"] == 0.0
    assert result["value"] is None
    assert "Insufficient historical data points" in result["details"]["reason"]

@pytest.mark.asyncio
@patch('redis.asyncio.client.Redis', new_callable=AsyncMock)
@patch('backend.agents.technical.momentum_agent.get_settings')
@patch('backend.agents.technical.momentum_agent.fetch_historical_price_series', new_callable=AsyncMock)
async def test_momentum_no_data_fetch_error(mock_fetch_hist, mock_get_settings, mock_redis, mock_settings):
    # Arrange
    mock_get_settings.return_value = mock_settings
    error_message = "API Error"
    mock_fetch_hist.side_effect = Exception(error_message)
    mock_redis.get.return_value = None

    # Act
    result = await momentum_run(SYMBOL)

    # Assert
    assert result["symbol"] == SYMBOL
    assert result["agent_name"] == agent_name
    assert result["verdict"] == "NO_DATA"
    assert result["confidence"] == 0.0
    assert result["value"] is None
    assert f"Failed to fetch historical prices: {error_message}" in result["details"]["reason"]

@pytest.mark.asyncio
@patch('redis.asyncio.client.Redis', new_callable=AsyncMock)
@patch('backend.agents.technical.momentum_agent.get_settings')
@patch('backend.agents.technical.momentum_agent.fetch_historical_price_series', new_callable=AsyncMock)
async def test_momentum_no_data_fetch_returns_none(mock_fetch_hist, mock_get_settings, mock_redis, mock_settings):
    # Arrange
    mock_get_settings.return_value = mock_settings
    mock_fetch_hist.return_value = None # Fetch returns None
    mock_redis.get.return_value = None

    # Act
    result = await momentum_run(SYMBOL)

    # Assert
    assert result["symbol"] == SYMBOL
    assert result["agent_name"] == agent_name
    assert result["verdict"] == "NO_DATA"
    assert result["confidence"] == 0.0
    assert result["value"] is None
    assert "Historical price data is missing or invalid" in result["details"]["reason"]

@pytest.mark.asyncio
@patch('redis.asyncio.client.Redis', new_callable=AsyncMock)
@patch('backend.agents.technical.momentum_agent.get_settings')
@patch('backend.agents.technical.momentum_agent.fetch_historical_price_series', new_callable=AsyncMock)
async def test_momentum_no_lookbacks_configured(mock_fetch_hist, mock_get_settings, mock_redis, mock_settings):
    # Arrange
    # Modify settings to have no lookbacks
    mock_settings.agent_settings.momentum.LOOKBACK_PERIODS = []
    mock_get_settings.return_value = mock_settings
    mock_fetch_hist.return_value = prices_positive # Doesn't matter as it exits early
    mock_redis.get.return_value = None

    # Act
    result = await momentum_run(SYMBOL)

    # Assert
    assert result["symbol"] == SYMBOL
    assert result["agent_name"] == agent_name
    assert result["verdict"] == "NO_DATA"
    assert result["confidence"] == 0.0
    assert result["value"] is None
    assert "Lookback periods not configured" in result["details"]["reason"]

@pytest.mark.asyncio
@patch('redis.asyncio.client.Redis', new_callable=AsyncMock)
@patch('backend.agents.technical.momentum_agent.get_settings')
@patch('backend.agents.technical.momentum_agent.fetch_historical_price_series', new_callable=AsyncMock)
async def test_momentum_partial_returns_calculable(mock_fetch_hist, mock_get_settings, mock_redis, mock_settings):
    # Arrange
    # Use data that's long enough for short periods but not the longest (252)
    partial_prices = generate_prices(100, 0.001, 0.015, 200) # Enough for 21, 63, 126 but not 252
    mock_get_settings.return_value = mock_settings
    mock_fetch_hist.return_value = partial_prices
    mock_redis.get.return_value = None

    # Act
    result = await momentum_run(SYMBOL)

    # Assert
    # Should still produce a verdict based on available periods
    assert result["symbol"] == SYMBOL
    assert result["agent_name"] == agent_name
    assert result["verdict"] != "NO_DATA" # Should calculate based on available data
    assert result["value"] is not None
    assert result["details"]["return_21d_pct"] is not None
    assert result["details"]["return_63d_pct"] is not None
    assert result["details"]["return_126d_pct"] is not None
    assert result["details"]["return_252d_pct"] is None # This one should be None
    assert result["details"]["average_momentum_pct"] is not None # Average of the valid ones

@pytest.mark.asyncio
@patch('redis.asyncio.client.Redis', new_callable=AsyncMock)
@patch('backend.agents.technical.momentum_agent.get_settings')
@patch('backend.agents.technical.momentum_agent.fetch_historical_price_series', new_callable=AsyncMock)
async def test_momentum_returns_with_nan_or_zero(mock_fetch_hist, mock_get_settings, mock_redis, mock_settings):
    # Arrange
    prices = prices_positive.copy()
    # Introduce NaN and zero at specific past points
    prices.iloc[-1 - 21] = np.nan # Affects 21d return
    prices.iloc[-1 - 63] = 0    # Affects 63d return
    mock_get_settings.return_value = mock_settings
    mock_fetch_hist.return_value = prices
    mock_redis.get.return_value = None

    # Act
    result = await momentum_run(SYMBOL)

    # Assert
    assert result["symbol"] == SYMBOL
    assert result["agent_name"] == agent_name
    assert result["verdict"] != "NO_DATA"
    assert result["value"] is not None
    assert result["details"]["return_21d_pct"] is None # Should be None due to NaN
    assert result["details"]["return_63d_pct"] is None # Should be None due to zero
    assert result["details"]["return_126d_pct"] is not None # Should be calculable
    assert result["details"]["return_252d_pct"] is not None # Should be calculable
    # Average should be based only on 126d and 252d returns
    valid_returns = [result["details"]["return_126d_pct"], result["details"]["return_252d_pct"]]
    expected_avg = np.mean([r / 100.0 for r in valid_returns if r is not None]) * 100
    assert result["details"]["average_momentum_pct"] == pytest.approx(expected_avg)
    assert result["value"] == pytest.approx(expected_avg)

