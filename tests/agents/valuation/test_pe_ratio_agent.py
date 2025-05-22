import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

import pytest
import asyncio
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock, AsyncMock

# Import the function to test and settings classes
from backend.agents.valuation.pe_ratio_agent import run as pe_ratio_run, agent_name
from backend.config.settings import Settings, AgentSettings, PeRatioAgentSettings

# Mock for get_redis_client
@pytest.fixture
def mock_get_redis_client():
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get = AsyncMock(return_value=None)
    mock_redis_instance.set = AsyncMock(return_value=True)
    mock_redis_instance.delete = AsyncMock(return_value=True)
    mock_redis_instance.ping = AsyncMock(return_value=True)

    async def fake_async_get_redis_client(*args, **kwargs):
        return mock_redis_instance

    # Patch where get_redis_client is imported by the decorator
    with patch("backend.agents.decorators.get_redis_client", new=fake_async_get_redis_client) as mock_func:
        yield mock_func

# Mock settings
@pytest.fixture
def mock_settings():
    settings = Settings()
    settings.agent_settings.pe_ratio = PeRatioAgentSettings(
        HISTORICAL_YEARS=1,
        PERCENTILE_UNDERVALUED=25.0,
        PERCENTILE_OVERVALUED=75.0
    )
    return settings

# Sample data
SYMBOL = "TEST"
CURRENT_PRICE = 100.0 # General current price, may be overridden in specific test logic
CURRENT_EPS = 10.0    # General current EPS, may be overridden for specific P/E targets
CURRENT_PE = CURRENT_PRICE / CURRENT_EPS # General P/E, may be overridden

# Generate dates for historical series
dates = pd.date_range(end=pd.Timestamp.today(), periods=252, freq='B') # Business days

# Define a stable target historical P/E ratio distribution for verdict-testing cases
# Mean chosen so P/E of 12 is 'FAIRLY_VALUED'. Std chosen for reasonable spread.
np.random.seed(42) # for reproducibility
stable_target_historical_pe_ratios = pd.Series(np.random.normal(loc=12, scale=3, size=252), index=dates, name="HistoricalPERatios")
# Ensure P/E ratios are positive, as negative P/E is handled differently
stable_target_historical_pe_ratios[stable_target_historical_pe_ratios <= 0] = 0.1 

# This global historical_prices_series is used by tests that don't involve dynamic EPS adjustments for verdict testing,
# or where the exact historical P/E distribution is not critical (e.g., NO_DATA tests).
np.random.seed(42) # Reset seed if needed for other random generations
historical_prices_raw = 120 + np.random.randn(252).cumsum() * 0.5 + np.random.normal(0, 5, 252)
historical_prices_raw[historical_prices_raw <= 0] = 1 # Ensure prices are positive
global_historical_prices_series = pd.Series(historical_prices_raw, index=dates)


@pytest.mark.asyncio
@patch('backend.agents.valuation.pe_ratio_agent.get_settings')
@patch('backend.agents.valuation.pe_ratio_agent.fetch_historical_price_series', new_callable=AsyncMock)
@patch('backend.agents.valuation.pe_ratio_agent.fetch_latest_eps', new_callable=AsyncMock)
@patch('backend.agents.valuation.pe_ratio_agent.fetch_price_point', new_callable=AsyncMock)
async def test_pe_ratio_undervalued(mock_fetch_price, mock_fetch_latest_eps, mock_fetch_hist, mock_get_settings, mock_settings, mock_get_redis_client):
    # Arrange
    mock_get_settings.return_value = mock_settings
    mock_fetch_price.return_value = {"price": CURRENT_PRICE}
    target_pe_undervalued = 8.0 # This P/E should be < 25th percentile of stable_target_historical_pe_ratios
    current_eps_for_test = CURRENT_PRICE / target_pe_undervalued
    mock_fetch_latest_eps.return_value = {"eps": current_eps_for_test}
    # Agent calculates historical P/E as: (historical_prices_series / current_eps_for_test)
    # We want this to be `stable_target_historical_pe_ratios`. So, historical_prices_series = stable_target_historical_pe_ratios * current_eps_for_test
    mock_fetch_hist.return_value = stable_target_historical_pe_ratios * current_eps_for_test

    # Act
    result = await pe_ratio_run(SYMBOL)

    # Assert
    assert result["symbol"] == SYMBOL
    assert result["agent_name"] == agent_name
    assert result["verdict"] == "UNDERVALUED_REL_HIST"
    assert result["value"] == target_pe_undervalued
    assert result["confidence"] > 0.6
    assert result["details"]["current_pe_ratio"] == target_pe_undervalued
    assert result["details"]["current_eps"] == round(current_eps_for_test, 2)
    assert result["details"]["current_price"] == CURRENT_PRICE
    assert result["details"]["historical_mean_pe"] is not None
    assert result["details"]["historical_std_dev_pe"] is not None
    assert result["details"]["percentile_rank"] < mock_settings.agent_settings.pe_ratio.PERCENTILE_UNDERVALUED
    assert result["details"]["z_score"] is not None
    assert result["details"]["data_source"] == "calculated_fundamental + historical_prices"
    assert result["details"]["config_used"]["historical_years"] == mock_settings.agent_settings.pe_ratio.HISTORICAL_YEARS

@pytest.mark.asyncio
@patch('backend.agents.valuation.pe_ratio_agent.get_settings')
@patch('backend.agents.valuation.pe_ratio_agent.fetch_historical_price_series', new_callable=AsyncMock)
@patch('backend.agents.valuation.pe_ratio_agent.fetch_latest_eps', new_callable=AsyncMock)
@patch('backend.agents.valuation.pe_ratio_agent.fetch_price_point', new_callable=AsyncMock)
async def test_pe_ratio_overvalued(mock_fetch_price, mock_fetch_latest_eps, mock_fetch_hist, mock_get_settings, mock_settings, mock_get_redis_client):
    # Arrange
    mock_get_settings.return_value = mock_settings
    mock_fetch_price.return_value = {"price": CURRENT_PRICE}
    target_pe_overvalued = 25.0 # This P/E should be > 75th percentile
    current_eps_for_test = CURRENT_PRICE / target_pe_overvalued
    mock_fetch_latest_eps.return_value = {"eps": current_eps_for_test}
    mock_fetch_hist.return_value = stable_target_historical_pe_ratios * current_eps_for_test

    # Act
    result = await pe_ratio_run(SYMBOL)

    # Assert
    assert result["symbol"] == SYMBOL
    assert result["agent_name"] == agent_name
    assert result["verdict"] == "OVERVALUED_REL_HIST"
    assert result["value"] == target_pe_overvalued
    assert result["confidence"] > 0.6
    assert result["details"]["percentile_rank"] >= mock_settings.agent_settings.pe_ratio.PERCENTILE_OVERVALUED
    assert result["details"]["z_score"] is not None
    assert result["details"]["current_eps"] == round(current_eps_for_test, 2)

@pytest.mark.asyncio
@patch('backend.agents.valuation.pe_ratio_agent.get_settings')
@patch('backend.agents.valuation.pe_ratio_agent.fetch_historical_price_series', new_callable=AsyncMock)
@patch('backend.agents.valuation.pe_ratio_agent.fetch_latest_eps', new_callable=AsyncMock)
@patch('backend.agents.valuation.pe_ratio_agent.fetch_price_point', new_callable=AsyncMock)
async def test_pe_ratio_fairly_valued(mock_fetch_price, mock_fetch_latest_eps, mock_fetch_hist, mock_get_settings, mock_settings, mock_get_redis_client):
    # Arrange
    mock_get_settings.return_value = mock_settings
    mock_fetch_price.return_value = {"price": CURRENT_PRICE}
    target_pe_fairly_valued = 12.0 # This P/E should be between 25th and 75th percentile
    current_eps_for_test = CURRENT_PRICE / target_pe_fairly_valued
    mock_fetch_latest_eps.return_value = {"eps": current_eps_for_test}
    mock_fetch_hist.return_value = stable_target_historical_pe_ratios * current_eps_for_test

    # Act
    result = await pe_ratio_run(SYMBOL)

    # Assert
    assert result["symbol"] == SYMBOL
    assert result["agent_name"] == agent_name
    assert result["verdict"] == "FAIRLY_VALUED_REL_HIST"
    assert result["value"] == target_pe_fairly_valued
    assert result["confidence"] == 0.5
    assert mock_settings.agent_settings.pe_ratio.PERCENTILE_UNDERVALUED <= result["details"]["percentile_rank"] < mock_settings.agent_settings.pe_ratio.PERCENTILE_OVERVALUED
    assert result["details"]["current_eps"] == round(current_eps_for_test, 2)

@pytest.mark.asyncio
@patch('backend.agents.valuation.pe_ratio_agent.get_settings')
@patch('backend.agents.valuation.pe_ratio_agent.fetch_historical_price_series', new_callable=AsyncMock)
@patch('backend.agents.valuation.pe_ratio_agent.fetch_latest_eps', new_callable=AsyncMock)
@patch('backend.agents.valuation.pe_ratio_agent.fetch_price_point', new_callable=AsyncMock)
async def test_pe_ratio_negative_earnings(mock_fetch_price, mock_fetch_latest_eps, mock_fetch_hist, mock_get_settings, mock_settings, mock_get_redis_client):
    # Arrange
    mock_get_settings.return_value = mock_settings
    mock_fetch_price.return_value = {"price": CURRENT_PRICE}
    mock_fetch_latest_eps.return_value = {"eps": -5.0}  # Negative EPS
    # For this test, the exact historical data content doesn't determine the verdict branch, use global series
    mock_fetch_hist.return_value = global_historical_prices_series 

    # Act
    result = await pe_ratio_run(SYMBOL)

    # Assert
    assert result["symbol"] == SYMBOL
    assert result["agent_name"] == agent_name
    assert result["verdict"] == "NEGATIVE_EARNINGS"
    assert result["value"] is None
    assert result["confidence"] == 0.7
    assert result["details"]["current_eps"] == -5.0
    assert "reason" in result["details"]

@pytest.mark.asyncio
@patch('backend.agents.valuation.pe_ratio_agent.get_settings')
@patch('backend.agents.valuation.pe_ratio_agent.fetch_historical_price_series', new_callable=AsyncMock)
@patch('backend.agents.valuation.pe_ratio_agent.fetch_latest_eps', new_callable=AsyncMock)
@patch('backend.agents.valuation.pe_ratio_agent.fetch_price_point', new_callable=AsyncMock)
async def test_pe_ratio_no_data_price(mock_fetch_price, mock_fetch_latest_eps, mock_fetch_hist, mock_get_settings, mock_settings, mock_get_redis_client):
    # Arrange
    mock_get_settings.return_value = mock_settings
    mock_fetch_price.return_value = None
    mock_fetch_latest_eps.return_value = {"eps": CURRENT_EPS}
    mock_fetch_hist.return_value = global_historical_prices_series

    # Act
    result = await pe_ratio_run(SYMBOL)

    # Assert
    assert result["symbol"] == SYMBOL
    assert result["agent_name"] == agent_name
    assert result["verdict"] == "NO_DATA"
    assert result["value"] is None
    assert result["confidence"] == 0.0
    assert "Missing or invalid current price" in result["details"]["reason"]

@pytest.mark.asyncio
@patch('backend.agents.valuation.pe_ratio_agent.get_settings')
@patch('backend.agents.valuation.pe_ratio_agent.fetch_historical_price_series', new_callable=AsyncMock)
@patch('backend.agents.valuation.pe_ratio_agent.fetch_latest_eps', new_callable=AsyncMock)
@patch('backend.agents.valuation.pe_ratio_agent.fetch_price_point', new_callable=AsyncMock)
async def test_pe_ratio_no_data_eps(mock_fetch_price, mock_fetch_latest_eps, mock_fetch_hist, mock_get_settings, mock_settings, mock_get_redis_client):
    # Arrange
    mock_get_settings.return_value = mock_settings
    mock_fetch_price.return_value = {"price": CURRENT_PRICE}
    mock_fetch_latest_eps.return_value = None  # Missing EPS
    mock_fetch_hist.return_value = global_historical_prices_series

    # Act
    result = await pe_ratio_run(SYMBOL)

    # Assert
    assert result["symbol"] == SYMBOL
    assert result["agent_name"] == agent_name
    assert result["verdict"] == "NO_DATA"
    assert result["value"] is None
    assert result["confidence"] == 0.0
    assert "Missing EPS data" in result["details"]["reason"]

@pytest.mark.asyncio
@patch('backend.agents.valuation.pe_ratio_agent.get_settings')
@patch('backend.agents.valuation.pe_ratio_agent.fetch_historical_price_series', new_callable=AsyncMock)
@patch('backend.agents.valuation.pe_ratio_agent.fetch_latest_eps', new_callable=AsyncMock)
@patch('backend.agents.valuation.pe_ratio_agent.fetch_price_point', new_callable=AsyncMock)
async def test_pe_ratio_no_historical_data(mock_fetch_price, mock_fetch_latest_eps, mock_fetch_hist, mock_get_settings, mock_settings, mock_get_redis_client):
    # Arrange
    mock_get_settings.return_value = mock_settings
    mock_fetch_price.return_value = {"price": CURRENT_PRICE}
    mock_fetch_latest_eps.return_value = {"eps": CURRENT_EPS}
    mock_fetch_hist.return_value = None # Missing historical data

    # Act
    result = await pe_ratio_run(SYMBOL)

    # Assert
    assert result["symbol"] == SYMBOL
    assert result["agent_name"] == agent_name
    assert result["verdict"] == "NO_HISTORICAL_CONTEXT"
    assert result["value"] == CURRENT_PE
    assert result["confidence"] == 0.3
    assert result["details"]["current_pe_ratio"] == CURRENT_PE
    assert result["details"]["historical_mean_pe"] is None
    assert result["details"]["historical_std_dev_pe"] is None
    assert result["details"]["percentile_rank"] is None
    assert result["details"]["z_score"] is None
    assert result["details"]["data_source"] == "calculated_fundamental"

@pytest.mark.asyncio
@patch('backend.agents.valuation.pe_ratio_agent.get_settings')
@patch('backend.agents.valuation.pe_ratio_agent.fetch_historical_price_series', new_callable=AsyncMock)
@patch('backend.agents.valuation.pe_ratio_agent.fetch_latest_eps', new_callable=AsyncMock)
@patch('backend.agents.valuation.pe_ratio_agent.fetch_price_point', new_callable=AsyncMock)
async def test_pe_ratio_fetch_error(mock_fetch_price, mock_fetch_latest_eps, mock_fetch_hist, mock_get_settings, mock_settings, mock_get_redis_client):
    # Arrange
    mock_get_settings.return_value = mock_settings
    error_message = "API limit reached"
    mock_fetch_price.side_effect = Exception(error_message)
    mock_fetch_latest_eps.return_value = {"eps": CURRENT_EPS}
    mock_fetch_hist.return_value = global_historical_prices_series

    # Act
    result = await pe_ratio_run(SYMBOL)

    # Assert
    assert result["symbol"] == SYMBOL
    assert result["agent_name"] == agent_name
    assert result["verdict"] == "NO_DATA"
    assert result["value"] is None
    assert result["confidence"] == 0.0
    assert f"Failed to fetch required data: {error_message}" in result["details"]["reason"]

@pytest.mark.asyncio
@patch('backend.agents.valuation.pe_ratio_agent.get_settings')
@patch('backend.agents.valuation.pe_ratio_agent.fetch_historical_price_series', new_callable=AsyncMock)
@patch('backend.agents.valuation.pe_ratio_agent.fetch_latest_eps', new_callable=AsyncMock)
@patch('backend.agents.valuation.pe_ratio_agent.fetch_price_point', new_callable=AsyncMock)
async def test_pe_ratio_historical_calc_empty(mock_fetch_price, mock_fetch_latest_eps, mock_fetch_hist, mock_get_settings, mock_settings, mock_get_redis_client):
    # Arrange
    mock_get_settings.return_value = mock_settings
    mock_fetch_price.return_value = {"price": CURRENT_PRICE}
    mock_fetch_latest_eps.return_value = {"eps": CURRENT_EPS}
    mock_fetch_hist.return_value = pd.Series(dtype=float) # Empty series for prices

    # Act
    result = await pe_ratio_run(SYMBOL)

    # Assert
    assert result["verdict"] == "NO_HISTORICAL_CONTEXT"
    assert result["value"] == CURRENT_PE

@pytest.mark.asyncio
@patch('backend.agents.valuation.pe_ratio_agent.get_settings')
@patch('backend.agents.valuation.pe_ratio_agent.fetch_historical_price_series', new_callable=AsyncMock)
@patch('backend.agents.valuation.pe_ratio_agent.fetch_latest_eps', new_callable=AsyncMock)
@patch('backend.agents.valuation.pe_ratio_agent.fetch_price_point', new_callable=AsyncMock)
async def test_pe_ratio_historical_insufficient_data(mock_fetch_price, mock_fetch_latest_eps, mock_fetch_hist, mock_get_settings, mock_settings, mock_get_redis_client):
    # Arrange
    mock_get_settings.return_value = mock_settings
    mock_fetch_price.return_value = {"price": CURRENT_PRICE}
    mock_fetch_latest_eps.return_value = {"eps": CURRENT_EPS} # CURRENT_PE will be 10.0
    # Historical P/Es: [8, 9, 10, 11, 12]
    # Percentile of 10.0 in [8,9,10,11,12] with kind='rank' is 60.0
    # (2 less, 1 equal) -> (2 + (1+1)/2) / 5 * 100 = 60.0
    # This falls into FAIRLY_VALUED (25 <= 60 < 75)
    short_prices = pd.Series([80, 90, 100, 110, 120], index=pd.date_range(end=pd.Timestamp.today(), periods=5, freq='B'))
    mock_fetch_hist.return_value = short_prices

    # Act
    result = await pe_ratio_run(SYMBOL)

    # Assert
    assert result["verdict"] == "FAIRLY_VALUED_REL_HIST"
    assert result["value"] == CURRENT_PE # 10.0
    assert result["details"]["percentile_rank"] == 60.0
