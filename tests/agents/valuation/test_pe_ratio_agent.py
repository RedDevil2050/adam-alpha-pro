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
CURRENT_PRICE = 100.0
CURRENT_EPS = 10.0
CURRENT_PE = 10.0 # 100 / 10

# Generate more realistic historical data (e.g., 252 days for 1 year)
dates = pd.date_range(end=pd.Timestamp.today(), periods=252, freq='B') # Business days
# Simulate some price movement around a mean PE of 12 (price around 120)
np.random.seed(42)
historical_prices_raw = 120 + np.random.randn(252).cumsum() * 0.5 + np.random.normal(0, 5, 252)
historical_prices_raw[historical_prices_raw <= 0] = 1 # Ensure prices are positive
historical_prices_series = pd.Series(historical_prices_raw, index=dates)

# Calculate expected historical PE series (using CURRENT_EPS for simplification as in agent)
historical_pe_series = historical_prices_series / CURRENT_EPS
expected_mean_hist_pe = historical_pe_series.mean()
expected_std_hist_pe = historical_pe_series.std()

# Calculate expected percentile rank (using scipy logic if available, else pandas)
try:
    from scipy import stats
    expected_percentile = stats.percentileofscore(historical_pe_series, CURRENT_PE, kind='rank')
except ImportError:
    expected_percentile = (historical_pe_series < CURRENT_PE).mean() * 100

# Calculate expected z-score
expected_z_score = (CURRENT_PE - expected_mean_hist_pe) / expected_std_hist_pe if expected_std_hist_pe > 1e-9 else None

@pytest.mark.asyncio
@patch('backend.agents.valuation.pe_ratio_agent.get_settings')
@patch('backend.agents.valuation.pe_ratio_agent.fetch_historical_price_series', new_callable=AsyncMock)
@patch("backend.utils.data_provider.fetch_eps_data", new_callable=AsyncMock)
@patch('backend.agents.valuation.pe_ratio_agent.fetch_price_point', new_callable=AsyncMock)
async def test_pe_ratio_undervalued(mock_fetch_price, mock_fetch_eps_data, mock_fetch_hist, mock_get_settings, mock_settings):
    # Arrange
    mock_get_settings.return_value = mock_settings
    mock_fetch_price.return_value = {"latestPrice": CURRENT_PRICE}
    # Make current PE low relative to history (e.g., 8)
    low_eps = CURRENT_PRICE / 8.0
    mock_fetch_eps_data.return_value = low_eps
    mock_fetch_hist.return_value = historical_prices_series

    # Act
    result = await pe_ratio_run(SYMBOL)

    # Assert
    assert result["symbol"] == SYMBOL
    assert result["agent_name"] == agent_name
    assert result["verdict"] == "UNDERVALUED_REL_HIST"
    assert result["value"] == 8.0
    assert result["confidence"] > 0.6 # Dynamic confidence
    assert result["details"]["current_pe_ratio"] == 8.0
    assert result["details"]["current_eps"] == round(low_eps, 2)
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
@patch("backend.utils.data_provider.fetch_eps_data", new_callable=AsyncMock)
@patch('backend.agents.valuation.pe_ratio_agent.fetch_price_point', new_callable=AsyncMock)
async def test_pe_ratio_overvalued(mock_fetch_price, mock_fetch_eps_data, mock_fetch_hist, mock_get_settings, mock_settings):
    # Arrange
    mock_get_settings.return_value = mock_settings
    mock_fetch_price.return_value = {"latestPrice": CURRENT_PRICE}
    # Make current PE high relative to history (e.g., 25)
    high_eps = CURRENT_PRICE / 25.0
    mock_fetch_eps_data.return_value = high_eps
    mock_fetch_hist.return_value = historical_prices_series

    # Act
    result = await pe_ratio_run(SYMBOL)

    # Assert
    assert result["symbol"] == SYMBOL
    assert result["agent_name"] == agent_name
    assert result["verdict"] == "OVERVALUED_REL_HIST"
    assert result["value"] == 25.0
    assert result["confidence"] > 0.6 # Dynamic confidence
    assert result["details"]["percentile_rank"] > mock_settings.agent_settings.pe_ratio.PERCENTILE_OVERVALUED
    assert result["details"]["z_score"] is not None

@pytest.mark.asyncio
@patch('backend.agents.valuation.pe_ratio_agent.get_settings')
@patch('backend.agents.valuation.pe_ratio_agent.fetch_historical_price_series', new_callable=AsyncMock)
@patch("backend.utils.data_provider.fetch_eps_data", new_callable=AsyncMock)
@patch('backend.agents.valuation.pe_ratio_agent.fetch_price_point', new_callable=AsyncMock)
async def test_pe_ratio_fairly_valued(mock_fetch_price, mock_fetch_eps_data, mock_fetch_hist, mock_get_settings, mock_settings):
    # Arrange
    mock_get_settings.return_value = mock_settings
    mock_fetch_price.return_value = {"latestPrice": CURRENT_PRICE}
    # Use EPS that results in PE within the fair range (e.g., 12)
    fair_eps = CURRENT_PRICE / 12.0
    mock_fetch_eps_data.return_value = fair_eps
    mock_fetch_hist.return_value = historical_prices_series

    # Act
    result = await pe_ratio_run(SYMBOL)

    # Assert
    assert result["symbol"] == SYMBOL
    assert result["agent_name"] == agent_name
    assert result["verdict"] == "FAIRLY_VALUED_REL_HIST"
    assert result["value"] == 12.0
    assert result["confidence"] == 0.5 # Neutral confidence
    assert mock_settings.agent_settings.pe_ratio.PERCENTILE_UNDERVALUED < result["details"]["percentile_rank"] < mock_settings.agent_settings.pe_ratio.PERCENTILE_OVERVALUED

@pytest.mark.asyncio
@patch('backend.agents.valuation.pe_ratio_agent.get_settings')
@patch('backend.agents.valuation.pe_ratio_agent.fetch_historical_price_series', new_callable=AsyncMock)
@patch("backend.utils.data_provider.fetch_eps_data", new_callable=AsyncMock)
@patch('backend.agents.valuation.pe_ratio_agent.fetch_price_point', new_callable=AsyncMock)
async def test_pe_ratio_negative_earnings(mock_fetch_price, mock_fetch_eps_data, mock_fetch_hist, mock_get_settings, mock_settings):
    # Arrange
    mock_get_settings.return_value = mock_settings
    mock_fetch_price.return_value = {"latestPrice": CURRENT_PRICE}
    mock_fetch_eps_data.return_value = -5.0  # Negative EPS
    mock_fetch_hist.return_value = historical_prices_series # Historical doesn't matter here

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
@patch("backend.utils.data_provider.fetch_eps_data", new_callable=AsyncMock)
@patch('backend.agents.valuation.pe_ratio_agent.fetch_price_point', new_callable=AsyncMock)
async def test_pe_ratio_no_data_price(mock_fetch_price, mock_fetch_eps_data, mock_fetch_hist, mock_get_settings, mock_settings):
    # Arrange
    mock_get_settings.return_value = mock_settings
    mock_fetch_price.return_value = None # Missing price
    mock_fetch_eps_data.return_value = CURRENT_EPS
    mock_fetch_hist.return_value = historical_prices_series

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
@patch("backend.utils.data_provider.fetch_eps_data", new_callable=AsyncMock)
@patch('backend.agents.valuation.pe_ratio_agent.fetch_price_point', new_callable=AsyncMock)
async def test_pe_ratio_no_data_eps(mock_fetch_price, mock_fetch_eps_data, mock_fetch_hist, mock_get_settings, mock_settings):
    # Arrange
    mock_get_settings.return_value = mock_settings
    mock_fetch_price.return_value = {"latestPrice": CURRENT_PRICE}
    mock_fetch_eps_data.return_value = None  # Missing EPS
    mock_fetch_hist.return_value = historical_prices_series

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
@patch("backend.utils.data_provider.fetch_eps_data", new_callable=AsyncMock)
@patch('backend.agents.valuation.pe_ratio_agent.fetch_price_point', new_callable=AsyncMock)
async def test_pe_ratio_no_historical_data(mock_fetch_price, mock_fetch_eps_data, mock_fetch_hist, mock_get_settings, mock_settings):
    # Arrange
    mock_get_settings.return_value = mock_settings
    mock_fetch_price.return_value = {"latestPrice": CURRENT_PRICE}
    mock_fetch_eps_data.return_value = CURRENT_EPS
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
@patch("backend.utils.data_provider.fetch_eps_data", new_callable=AsyncMock)
@patch('backend.agents.valuation.pe_ratio_agent.fetch_price_point', new_callable=AsyncMock)
async def test_pe_ratio_fetch_error(mock_fetch_price, mock_fetch_eps_data, mock_fetch_hist, mock_get_settings, mock_settings):
    # Arrange
    mock_get_settings.return_value = mock_settings
    error_message = "API limit reached"
    mock_fetch_price.side_effect = Exception(error_message) # Simulate error during fetch
    mock_fetch_eps_data.return_value = CURRENT_EPS
    mock_fetch_hist.return_value = historical_prices_series

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
@patch("backend.utils.data_provider.fetch_eps_data", new_callable=AsyncMock)
@patch('backend.agents.valuation.pe_ratio_agent.fetch_price_point', new_callable=AsyncMock)
async def test_pe_ratio_historical_calc_empty(mock_fetch_price, mock_fetch_eps_data, mock_fetch_hist, mock_get_settings, mock_settings):
    # Arrange
    mock_get_settings.return_value = mock_settings
    mock_fetch_price.return_value = {"latestPrice": CURRENT_PRICE}
    mock_fetch_eps_data.return_value = CURRENT_EPS
    # Provide historical prices that become all NaN when divided by EPS (e.g., all zeros)
    empty_hist = pd.Series([0.0] * 252, index=historical_prices_series.index)
    mock_fetch_hist.return_value = empty_hist

    # Act
    result = await pe_ratio_run(SYMBOL)

    # Assert
    assert result["symbol"] == SYMBOL
    assert result["agent_name"] == agent_name
    assert result["verdict"] == "NO_HISTORICAL_CONTEXT"
    assert result["value"] == CURRENT_PE
    assert result["confidence"] == 0.3
    assert result["details"]["historical_mean_pe"] is None
    assert result["details"]["percentile_rank"] is None
    assert result["details"]["z_score"] is None
    assert "historical calc failed" in result["details"]["data_source"]

# Add test for scipy import failure if needed, though mocking import is complex
# Test case for invalid historical data format (e.g., list instead of Series/dict)
@pytest.mark.asyncio
@patch('backend.agents.valuation.pe_ratio_agent.get_settings')
@patch('backend.agents.valuation.pe_ratio_agent.fetch_historical_price_series', new_callable=AsyncMock)
@patch("backend.utils.data_provider.fetch_eps_data", new_callable=AsyncMock)
@patch('backend.agents.valuation.pe_ratio_agent.fetch_price_point', new_callable=AsyncMock)
async def test_pe_ratio_invalid_hist_format(mock_fetch_price, mock_fetch_eps_data, mock_fetch_hist, mock_get_settings, mock_settings):
    # Arrange
    mock_get_settings.return_value = mock_settings
    mock_fetch_price.return_value = {"latestPrice": CURRENT_PRICE}
    mock_fetch_eps_data.return_value = CURRENT_EPS
    mock_fetch_hist.return_value = [100, 101, 102] # Invalid list format

    # Act
    result = await pe_ratio_run(SYMBOL)

    # Assert
    assert result["verdict"] == "NO_HISTORICAL_CONTEXT"
    assert result["details"]["data_source"] == "calculated_fundamental (invalid historical data)"
    assert result["details"]["percentile_rank"] is None
    assert result["details"]["z_score"] is None
