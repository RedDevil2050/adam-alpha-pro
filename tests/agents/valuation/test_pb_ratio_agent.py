import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

import pytest
import asyncio
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock, AsyncMock

# Import the function to test and settings classes
from backend.agents.valuation.pb_ratio_agent import run as pb_ratio_run, agent_name
from backend.config.settings import Settings, AgentSettings, PbRatioAgentSettings

# Mock settings
@pytest.fixture
def mock_settings():
    settings = Settings()
    settings.agent_settings.pb_ratio = PbRatioAgentSettings(
        HISTORICAL_YEARS=1,
        PERCENTILE_UNDERVALUED=25.0,
        PERCENTILE_OVERVALUED=75.0
    )
    return settings

# Sample data
SYMBOL = "TEST"
CURRENT_PRICE = 100.0
CURRENT_BVPS = 50.0 # Book Value Per Share
CURRENT_PB = 2.0 # 100 / 50

# Generate more realistic historical data (e.g., 252 days for 1 year)
dates = pd.date_range(end=pd.Timestamp.today(), periods=252, freq='B') # Business days
# Simulate some price movement around a mean price of 80 (lower than CURRENT_PRICE=100)
np.random.seed(42)
# Centered around 80 instead of 120, adjusted noise scaling
historical_prices_raw = 80 + np.random.randn(252).cumsum() * 0.4 + np.random.normal(0, 4, 252)
historical_prices_raw[historical_prices_raw <= 0] = 1 # Ensure prices are positive
historical_prices_series = pd.Series(historical_prices_raw, index=dates)

# Calculate expected historical PB series (using CURRENT_BVPS for simplification as in agent)
historical_pb_series = historical_prices_series / CURRENT_BVPS
expected_mean_hist_pb = historical_pb_series.mean()
expected_std_hist_pb = historical_pb_series.std()

# Calculate expected percentile rank (using scipy logic if available, else pandas)
try:
    from scipy import stats
    expected_percentile = stats.percentileofscore(historical_pb_series, CURRENT_PB, kind='rank')
except ImportError:
    expected_percentile = (historical_pb_series < CURRENT_PB).mean() * 100

# Calculate expected z-score
expected_z_score = (CURRENT_PB - expected_mean_hist_pb) / expected_std_hist_pb if expected_std_hist_pb > 1e-9 else None

@pytest.mark.asyncio
@patch('backend.agents.valuation.pb_ratio_agent.get_settings')
@patch('backend.agents.valuation.pb_ratio_agent.fetch_historical_price_series', new_callable=AsyncMock)
@patch('backend.agents.valuation.pb_ratio_agent.fetch_latest_bvps', new_callable=AsyncMock)
@patch('backend.agents.valuation.pb_ratio_agent.fetch_price_point', new_callable=AsyncMock)
async def test_pb_ratio_undervalued(mock_fetch_price, mock_fetch_bvps, mock_fetch_hist, mock_get_settings, mock_settings):
    # Arrange
    mock_get_settings.return_value = mock_settings
    mock_fetch_price.return_value = {"latestPrice": CURRENT_PRICE}
    # Make current PB low relative to history (e.g., 1.0)
    high_bvps = CURRENT_PRICE / 1.0
    # Return a dictionary as expected by the agent
    mock_fetch_bvps.return_value = {"bookValuePerShare": high_bvps}
    mock_fetch_hist.return_value = historical_prices_series

    # Act
    result = await pb_ratio_run(SYMBOL)

    # Assert
    assert result["symbol"] == SYMBOL
    assert result["agent_name"] == agent_name
    assert result["verdict"] == "UNDERVALUED_REL_HIST"
    assert result["value"] == 1.0
    assert result["confidence"] > 0.6 # Dynamic confidence
    assert result["details"]["current_pb_ratio"] == 1.0
    assert result["details"]["current_bvps"] == round(high_bvps, 2)
    assert result["details"]["current_price"] == CURRENT_PRICE
    assert result["details"]["historical_mean_pb"] is not None
    assert result["details"]["historical_std_dev_pb"] is not None
    assert result["details"]["percentile_rank"] < mock_settings.agent_settings.pb_ratio.PERCENTILE_UNDERVALUED
    assert result["details"]["z_score"] is not None
    assert result["details"]["data_source"] == "calculated_fundamental + historical_prices"
    assert result["details"]["config_used"]["historical_years"] == mock_settings.agent_settings.pb_ratio.HISTORICAL_YEARS

@pytest.mark.asyncio
@patch('backend.agents.valuation.pb_ratio_agent.get_settings')
@patch('backend.agents.valuation.pb_ratio_agent.fetch_historical_price_series', new_callable=AsyncMock)
@patch('backend.agents.valuation.pb_ratio_agent.fetch_latest_bvps', new_callable=AsyncMock)
@patch('backend.agents.valuation.pb_ratio_agent.fetch_price_point', new_callable=AsyncMock)
async def test_pb_ratio_overvalued(mock_fetch_price, mock_fetch_bvps, mock_fetch_hist, mock_get_settings, mock_settings):
    # Arrange
    mock_get_settings.return_value = mock_settings
    mock_fetch_price.return_value = {"latestPrice": CURRENT_PRICE}
    # Make current PB high relative to history (e.g., 4.0)
    low_bvps = CURRENT_PRICE / 4.0
    # Return a dictionary as expected by the agent
    mock_fetch_bvps.return_value = {"bookValuePerShare": low_bvps}
    mock_fetch_hist.return_value = historical_prices_series

    # Act
    result = await pb_ratio_run(SYMBOL)

    # Assert
    assert result["symbol"] == SYMBOL
    assert result["agent_name"] == agent_name
    assert result["verdict"] == "OVERVALUED_REL_HIST"
    assert result["value"] == 4.0
    assert result["confidence"] > 0.6 # Dynamic confidence
    assert result["details"]["percentile_rank"] > mock_settings.agent_settings.pb_ratio.PERCENTILE_OVERVALUED
    assert result["details"]["z_score"] is not None

@pytest.mark.asyncio
@patch('backend.agents.valuation.pb_ratio_agent.get_settings')
@patch('backend.agents.valuation.pb_ratio_agent.fetch_historical_price_series', new_callable=AsyncMock)
@patch('backend.agents.valuation.pb_ratio_agent.fetch_latest_bvps', new_callable=AsyncMock)
@patch('backend.agents.valuation.pb_ratio_agent.fetch_price_point', new_callable=AsyncMock)
async def test_pb_ratio_fairly_valued(mock_fetch_price, mock_fetch_bvps, mock_fetch_hist, mock_get_settings, mock_settings):
    # Arrange
    mock_get_settings.return_value = mock_settings
    mock_fetch_price.return_value = {"latestPrice": CURRENT_PRICE}
    # Use BVPS that results in PB within the fair range (e.g., 2.5)
    fair_bvps = CURRENT_PRICE / 2.5
    # Return a dictionary as expected by the agent
    mock_fetch_bvps.return_value = {"bookValuePerShare": fair_bvps}
    mock_fetch_hist.return_value = historical_prices_series

    # Act
    result = await pb_ratio_run(SYMBOL)

    # Assert
    assert result["symbol"] == SYMBOL
    assert result["agent_name"] == agent_name
    assert result["verdict"] == "FAIRLY_VALUED_REL_HIST"
    assert result["value"] == 2.5
    assert result["confidence"] == 0.5 # Neutral confidence
    assert mock_settings.agent_settings.pb_ratio.PERCENTILE_UNDERVALUED < result["details"]["percentile_rank"] < mock_settings.agent_settings.pb_ratio.PERCENTILE_OVERVALUED

@pytest.mark.asyncio
@patch('backend.agents.valuation.pb_ratio_agent.get_settings')
@patch('backend.agents.valuation.pb_ratio_agent.fetch_historical_price_series', new_callable=AsyncMock)
@patch('backend.agents.valuation.pb_ratio_agent.fetch_latest_bvps', new_callable=AsyncMock)
@patch('backend.agents.valuation.pb_ratio_agent.fetch_price_point', new_callable=AsyncMock)
async def test_pb_ratio_negative_or_zero_bv(mock_fetch_price, mock_fetch_bvps, mock_fetch_hist, mock_get_settings, mock_settings):
    # Arrange
    mock_get_settings.return_value = mock_settings
    mock_fetch_price.return_value = {"latestPrice": CURRENT_PRICE}
    # Return a dictionary as expected by the agent
    mock_fetch_bvps.return_value = {"bookValuePerShare": -10.0} # Negative BVPS
    mock_fetch_hist.return_value = historical_prices_series # Historical doesn't matter here

    # Act
    result = await pb_ratio_run(SYMBOL)

    # Assert
    assert result["symbol"] == SYMBOL
    assert result["agent_name"] == agent_name
    assert result["verdict"] == "NEGATIVE_OR_ZERO_BV"
    assert result["value"] is None
    assert result["confidence"] == 0.7
    assert result["details"]["current_bvps"] == -10.0
    assert "reason" in result["details"]

@pytest.mark.asyncio
@patch('backend.agents.valuation.pb_ratio_agent.get_settings')
@patch('backend.agents.valuation.pb_ratio_agent.fetch_historical_price_series', new_callable=AsyncMock)
@patch('backend.agents.valuation.pb_ratio_agent.fetch_latest_bvps', new_callable=AsyncMock)
@patch('backend.agents.valuation.pb_ratio_agent.fetch_price_point', new_callable=AsyncMock)
async def test_pb_ratio_no_data_price(mock_fetch_price, mock_fetch_bvps, mock_fetch_hist, mock_get_settings, mock_settings):
    # Arrange
    mock_get_settings.return_value = mock_settings
    mock_fetch_price.return_value = None # Missing price
    # Return a dictionary as expected by the agent
    mock_fetch_bvps.return_value = {"bookValuePerShare": CURRENT_BVPS}
    mock_fetch_hist.return_value = historical_prices_series

    # Act
    result = await pb_ratio_run(SYMBOL)

    # Assert
    assert result["symbol"] == SYMBOL
    assert result["agent_name"] == agent_name
    assert result["verdict"] == "NO_DATA"
    assert result["value"] is None
    assert result["confidence"] == 0.0
    assert "Missing or invalid current price" in result["details"]["reason"]

@pytest.mark.asyncio
@patch('backend.agents.valuation.pb_ratio_agent.get_settings')
@patch('backend.agents.valuation.pb_ratio_agent.fetch_historical_price_series', new_callable=AsyncMock)
@patch('backend.agents.valuation.pb_ratio_agent.fetch_latest_bvps', new_callable=AsyncMock)
@patch('backend.agents.valuation.pb_ratio_agent.fetch_price_point', new_callable=AsyncMock)
async def test_pb_ratio_no_data_bvps(mock_fetch_price, mock_fetch_bvps, mock_fetch_hist, mock_get_settings, mock_settings):
    # Arrange
    mock_get_settings.return_value = mock_settings
    mock_fetch_price.return_value = {"latestPrice": CURRENT_PRICE}
    mock_fetch_bvps.return_value = None # Missing BVPS
    mock_fetch_hist.return_value = historical_prices_series

    # Act
    result = await pb_ratio_run(SYMBOL)

    # Assert
    assert result["symbol"] == SYMBOL
    assert result["agent_name"] == agent_name
    assert result["verdict"] == "NO_DATA"
    assert result["value"] is None
    assert result["confidence"] == 0.0
    assert "Missing Book Value Per Share (BVPS) data" in result["details"]["reason"]

@pytest.mark.asyncio
@patch('backend.agents.valuation.pb_ratio_agent.get_settings')
@patch('backend.agents.valuation.pb_ratio_agent.fetch_historical_price_series', new_callable=AsyncMock)
@patch('backend.agents.valuation.pb_ratio_agent.fetch_latest_bvps', new_callable=AsyncMock)
@patch('backend.agents.valuation.pb_ratio_agent.fetch_price_point', new_callable=AsyncMock)
async def test_pb_ratio_no_historical_data(mock_fetch_price, mock_fetch_bvps, mock_fetch_hist, mock_get_settings, mock_settings):
    # Arrange
    mock_get_settings.return_value = mock_settings
    mock_fetch_price.return_value = {"latestPrice": CURRENT_PRICE}
    # Return a dictionary as expected by the agent
    mock_fetch_bvps.return_value = {"bookValuePerShare": CURRENT_BVPS}
    mock_fetch_hist.return_value = None # Missing historical data

    # Act
    result = await pb_ratio_run(SYMBOL)

    # Assert
    assert result["symbol"] == SYMBOL
    assert result["agent_name"] == agent_name
    assert result["verdict"] == "NO_HISTORICAL_CONTEXT"
    assert result["value"] == CURRENT_PB
    assert result["confidence"] == 0.3
    assert result["details"]["current_pb_ratio"] == CURRENT_PB
    assert result["details"]["historical_mean_pb"] is None
    assert result["details"]["historical_std_dev_pb"] is None
    assert result["details"]["percentile_rank"] is None
    assert result["details"]["z_score"] is None
    assert result["details"]["data_source"] == "calculated_fundamental"

@pytest.mark.asyncio
@patch('backend.agents.valuation.pb_ratio_agent.get_settings')
@patch('backend.agents.valuation.pb_ratio_agent.fetch_historical_price_series', new_callable=AsyncMock)
@patch('backend.agents.valuation.pb_ratio_agent.fetch_latest_bvps', new_callable=AsyncMock)
@patch('backend.agents.valuation.pb_ratio_agent.fetch_price_point', new_callable=AsyncMock)
async def test_pb_ratio_fetch_error(mock_fetch_price, mock_fetch_bvps, mock_fetch_hist, mock_get_settings, mock_settings):
    # Arrange
    mock_get_settings.return_value = mock_settings
    error_message = "API limit reached"
    mock_fetch_bvps.side_effect = Exception(error_message) # Simulate error during fetch
    mock_fetch_price.return_value = {"latestPrice": CURRENT_PRICE}
    # Although fetch_bvps raises an error, ensure the mock setup is consistent if needed elsewhere
    # mock_fetch_bvps.return_value = {"bookValuePerShare": CURRENT_BVPS} # This line is effectively ignored due to side_effect
    mock_fetch_hist.return_value = historical_prices_series

    # Act
    result = await pb_ratio_run(SYMBOL)

    # Assert
    assert result["symbol"] == SYMBOL
    assert result["agent_name"] == agent_name
    assert result["verdict"] == "NO_DATA"
    assert result["value"] is None
    assert result["confidence"] == 0.0
    assert f"Failed to fetch required data: {error_message}" in result["details"]["reason"]

@pytest.mark.asyncio
@patch('backend.agents.valuation.pb_ratio_agent.get_settings')
@patch('backend.agents.valuation.pb_ratio_agent.fetch_historical_price_series', new_callable=AsyncMock)
@patch('backend.agents.valuation.pb_ratio_agent.fetch_latest_bvps', new_callable=AsyncMock)
@patch('backend.agents.valuation.pb_ratio_agent.fetch_price_point', new_callable=AsyncMock)
async def test_pb_ratio_historical_calc_empty(mock_fetch_price, mock_fetch_bvps, mock_fetch_hist, mock_get_settings, mock_settings):
    # Arrange
    mock_get_settings.return_value = mock_settings
    mock_fetch_price.return_value = {"latestPrice": CURRENT_PRICE}
    # Return a dictionary as expected by the agent
    mock_fetch_bvps.return_value = {"bookValuePerShare": CURRENT_BVPS}
    # Provide historical prices that become all NaN when divided by BVPS (e.g., all zeros)
    empty_hist = pd.Series([0.0] * 252, index=historical_prices_series.index)
    mock_fetch_hist.return_value = empty_hist

    # Act
    result = await pb_ratio_run(SYMBOL)

    # Assert
    assert result["symbol"] == SYMBOL
    assert result["agent_name"] == agent_name
    assert result["verdict"] == "NO_HISTORICAL_CONTEXT"
    assert result["value"] == CURRENT_PB
    assert result["confidence"] == 0.3
    assert result["details"]["historical_mean_pb"] is None
    assert result["details"]["percentile_rank"] is None
    assert result["details"]["z_score"] is None
    assert "historical calc failed" in result["details"]["data_source"]

# Test case for invalid historical data format (e.g., list instead of Series/dict)
@pytest.mark.asyncio
@patch('backend.agents.valuation.pb_ratio_agent.get_settings')
@patch('backend.agents.valuation.pb_ratio_agent.fetch_historical_price_series', new_callable=AsyncMock)
@patch('backend.agents.valuation.pb_ratio_agent.fetch_latest_bvps', new_callable=AsyncMock)
@patch('backend.agents.valuation.pb_ratio_agent.fetch_price_point', new_callable=AsyncMock)
async def test_pb_ratio_invalid_hist_format(mock_fetch_price, mock_fetch_bvps, mock_fetch_hist, mock_get_settings, mock_settings):
    # Arrange
    mock_get_settings.return_value = mock_settings
    mock_fetch_price.return_value = {"latestPrice": CURRENT_PRICE}
    # Return a dictionary as expected by the agent
    mock_fetch_bvps.return_value = {"bookValuePerShare": CURRENT_BVPS}
    mock_fetch_hist.return_value = [100, 101, 102] # Invalid list format

    # Act
    result = await pb_ratio_run(SYMBOL)

    # Assert
    assert result["verdict"] == "NO_HISTORICAL_CONTEXT"
    assert result["details"]["data_source"] == "calculated_fundamental (invalid historical data)"
    assert result["details"]["percentile_rank"] is None
    assert result["details"]["z_score"] is None
