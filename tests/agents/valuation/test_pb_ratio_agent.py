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
    settings.agent_settings.pb_ratio = PbRatioAgentSettings(
        HISTORICAL_YEARS=1,
        PERCENTILE_UNDERVALUED=25.0,
        PERCENTILE_OVERVALUED=75.0
    )
    return settings

# Sample data
SYMBOL = "TEST"
CURRENT_PRICE = 100.0
CURRENT_BVPS = 50.0 # Book Value Per Share for general context, may be overridden in tests
CURRENT_PB = CURRENT_PRICE / CURRENT_BVPS # General P/B, may be overridden by test logic

# Generate more realistic historical data (e.g., 252 days for 1 year)
dates = pd.date_range(end=pd.Timestamp.today(), periods=252, freq='B') # Business days
# Simulate some price movement around CURRENT_PRICE
np.random.seed(42)
# This historical_prices_series is used by tests that don't involve dynamic BVPS adjustments for verdict testing.
historical_prices_raw = CURRENT_PRICE + np.random.randn(252).cumsum() * 0.4 + np.random.normal(0, 4, 252)
historical_prices_raw[historical_prices_raw <= 0] = 1 # Ensure prices are positive
global_historical_prices_series = pd.Series(historical_prices_raw, index=dates)

# Define a stable target historical P/B ratio distribution for verdict-testing cases
# Mean chosen so P/B of 2.5 is 'FAIRLY_VALUED'. Std chosen for reasonable spread.
# Using seed 42 for reproducibility as used elsewhere.
np.random.seed(42)
stable_target_historical_pb_ratios = pd.Series(np.random.normal(loc=2.5, scale=0.8, size=252), index=dates, name="HistoricalPBRatios")

# The following calculations are for general reference or older logic, specific tests will mock appropriately.
# Calculate expected historical PB series (using general CURRENT_BVPS for simplification as in agent)
# Recalculate based on the potentially modified historical_prices_series
# historical_pb_series = global_historical_prices_series / CURRENT_BVPS
# expected_mean_hist_pb = historical_pb_series.mean()
# expected_std_hist_pb = historical_pb_series.std()

# Calculate expected percentile rank (using scipy logic if available, else pandas)
# try:
#     from scipy import stats
#     expected_percentile = stats.percentileofscore(historical_pb_series, CURRENT_PB, kind='rank')
# except ImportError:
#     expected_percentile = (historical_pb_series < CURRENT_PB).mean() * 100

# Calculate expected z-score
# expected_z_score = (CURRENT_PB - expected_mean_hist_pb) / expected_std_hist_pb if expected_std_hist_pb > 1e-9 else None

@pytest.mark.asyncio
@patch('backend.agents.valuation.pb_ratio_agent.get_settings')
@patch('backend.agents.valuation.pb_ratio_agent.fetch_historical_price_series', new_callable=AsyncMock)
@patch('backend.agents.valuation.pb_ratio_agent.fetch_latest_bvps', new_callable=AsyncMock)
@patch('backend.agents.valuation.pb_ratio_agent.fetch_price_point', new_callable=AsyncMock)
async def test_pb_ratio_undervalued(mock_fetch_price, mock_fetch_bvps, mock_fetch_hist, mock_get_settings, mock_settings, mock_get_redis_client):
    # Arrange
    mock_get_settings.return_value = mock_settings
    mock_fetch_price.return_value = {"latestPrice": CURRENT_PRICE}
    # Make current PB low relative to history (e.g., 1.0)
    target_pb_undervalued = 1.0
    current_bvps_for_test = CURRENT_PRICE / target_pb_undervalued
    mock_fetch_bvps.return_value = {"bookValuePerShare": current_bvps_for_test}
    # Agent will calculate historical P/B as: (stable_target_historical_pb_ratios * current_bvps_for_test) / current_bvps_for_test
    mock_fetch_hist.return_value = stable_target_historical_pb_ratios * current_bvps_for_test

    # Act
    result = await pb_ratio_run(SYMBOL)

    # Assert
    assert result["symbol"] == SYMBOL
    assert result["agent_name"] == agent_name
    assert result["verdict"] == "UNDERVALUED_REL_HIST"
    assert result["value"] == target_pb_undervalued
    assert result["confidence"] > 0.6 # Confidence for UNDERVALUED
    assert result["details"]["current_pb_ratio"] == target_pb_undervalued
    assert result["details"]["current_bvps"] == round(current_bvps_for_test, 2)
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
async def test_pb_ratio_overvalued(mock_fetch_price, mock_fetch_bvps, mock_fetch_hist, mock_get_settings, mock_settings, mock_get_redis_client):
    # Arrange
    mock_get_settings.return_value = mock_settings
    mock_fetch_price.return_value = {"latestPrice": CURRENT_PRICE}
    # Make current PB high relative to history (e.g., 4.0)
    target_pb_overvalued = 4.0
    current_bvps_for_test = CURRENT_PRICE / target_pb_overvalued
    mock_fetch_bvps.return_value = {"bookValuePerShare": current_bvps_for_test}
    mock_fetch_hist.return_value = stable_target_historical_pb_ratios * current_bvps_for_test

    # Act
    result = await pb_ratio_run(SYMBOL)

    # Assert
    assert result["symbol"] == SYMBOL
    assert result["agent_name"] == agent_name
    assert result["verdict"] == "OVERVALUED_REL_HIST"
    assert result["value"] == target_pb_overvalued
    # With percentile for 4.0 being ~97%, confidence should be well > 0.6
    assert result["confidence"] > 0.6 
    assert result["details"]["percentile_rank"] >= mock_settings.agent_settings.pb_ratio.PERCENTILE_OVERVALUED
    assert result["details"]["z_score"] is not None

@pytest.mark.asyncio
@patch('backend.agents.valuation.pb_ratio_agent.get_settings')
@patch('backend.agents.valuation.pb_ratio_agent.fetch_historical_price_series', new_callable=AsyncMock)
@patch('backend.agents.valuation.pb_ratio_agent.fetch_latest_bvps', new_callable=AsyncMock)
@patch('backend.agents.valuation.pb_ratio_agent.fetch_price_point', new_callable=AsyncMock)
async def test_pb_ratio_fairly_valued(mock_fetch_price, mock_fetch_bvps, mock_fetch_hist, mock_get_settings, mock_settings, mock_get_redis_client):
    # Arrange
    mock_get_settings.return_value = mock_settings
    mock_fetch_price.return_value = {"latestPrice": CURRENT_PRICE}
    # Use BVPS that results in PB within the fair range (e.g., 2.5)
    target_pb_fairly_valued = 2.5
    current_bvps_for_test = CURRENT_PRICE / target_pb_fairly_valued
    mock_fetch_bvps.return_value = {"bookValuePerShare": current_bvps_for_test}
    mock_fetch_hist.return_value = stable_target_historical_pb_ratios * current_bvps_for_test

    # Act
    result = await pb_ratio_run(SYMBOL)

    # Assert
    assert result["symbol"] == SYMBOL
    assert result["agent_name"] == agent_name
    assert result["verdict"] == "FAIRLY_VALUED_REL_HIST"
    assert result["value"] == target_pb_fairly_valued
    assert result["confidence"] == 0.5 # Confidence for FAIRLY_VALUED
    assert mock_settings.agent_settings.pb_ratio.PERCENTILE_UNDERVALUED <= result["details"]["percentile_rank"] < mock_settings.agent_settings.pb_ratio.PERCENTILE_OVERVALUED
    # ...existing code...

@pytest.mark.asyncio
@patch('backend.agents.valuation.pb_ratio_agent.get_settings')
@patch('backend.agents.valuation.pb_ratio_agent.fetch_historical_price_series', new_callable=AsyncMock)
@patch('backend.agents.valuation.pb_ratio_agent.fetch_latest_bvps', new_callable=AsyncMock)
@patch('backend.agents.valuation.pb_ratio_agent.fetch_price_point', new_callable=AsyncMock)
async def test_pb_ratio_negative_or_zero_bv(mock_fetch_price, mock_fetch_bvps, mock_fetch_hist, mock_get_settings, mock_settings, mock_get_redis_client):
    # Arrange
    mock_get_settings.return_value = mock_settings
    mock_fetch_price.return_value = {"latestPrice": CURRENT_PRICE}
    mock_fetch_bvps.return_value = {"bookValuePerShare": -10.0} # Negative BVPS
    # For this test, the exact historical data content doesn't determine the verdict branch
    mock_fetch_hist.return_value = global_historical_prices_series 

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
async def test_pb_ratio_no_data_price(mock_fetch_price, mock_fetch_bvps, mock_fetch_hist, mock_get_settings, mock_settings, mock_get_redis_client):
    # Arrange
    mock_get_settings.return_value = mock_settings
    mock_fetch_price.return_value = None # Missing price
    mock_fetch_bvps.return_value = {"bookValuePerShare": CURRENT_BVPS}
    mock_fetch_hist.return_value = global_historical_prices_series

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
async def test_pb_ratio_no_data_bvps(mock_fetch_price, mock_fetch_bvps, mock_fetch_hist, mock_get_settings, mock_settings, mock_get_redis_client):
    # Arrange
    mock_get_settings.return_value = mock_settings
    mock_fetch_price.return_value = {"latestPrice": CURRENT_PRICE}
    mock_fetch_bvps.return_value = None # Missing BVPS
    mock_fetch_hist.return_value = global_historical_prices_series

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
async def test_pb_ratio_no_historical_data(mock_fetch_price, mock_fetch_bvps, mock_fetch_hist, mock_get_settings, mock_settings, mock_get_redis_client):
    # Arrange
    mock_get_settings.return_value = mock_settings
    mock_fetch_price.return_value = {"latestPrice": CURRENT_PRICE}
    mock_fetch_bvps.return_value = {"bookValuePerShare": CURRENT_BVPS}
    mock_fetch_hist.return_value = None # Missing historical data

    # Act
    result = await pb_ratio_run(SYMBOL)

    # Assert
    assert result["symbol"] == SYMBOL
    assert result["agent_name"] == agent_name
    assert result["verdict"] == "NO_HISTORICAL_CONTEXT"
    # CURRENT_PB is 2.0 (100/50)
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
async def test_pb_ratio_fetch_error(mock_fetch_price, mock_fetch_bvps, mock_fetch_hist, mock_get_settings, mock_settings, mock_get_redis_client):
    # Arrange
    mock_get_settings.return_value = mock_settings
    error_message = "API limit reached"
    mock_fetch_bvps.side_effect = Exception(error_message) # Simulate error during fetch
    mock_fetch_price.return_value = {"latestPrice": CURRENT_PRICE}
    mock_fetch_hist.return_value = global_historical_prices_series

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
async def test_pb_ratio_historical_calc_empty(mock_fetch_price, mock_fetch_bvps, mock_fetch_hist, mock_get_settings, mock_settings, mock_get_redis_client):
    # Arrange
    mock_get_settings.return_value = mock_settings
    mock_fetch_price.return_value = {"latestPrice": CURRENT_PRICE}
    mock_fetch_bvps.return_value = {"bookValuePerShare": CURRENT_BVPS}
    mock_fetch_hist.return_value = pd.Series(dtype=float) # Empty series

    # Act
    result = await pb_ratio_run(SYMBOL)

    # Assert
    assert result["verdict"] == "NO_HISTORICAL_CONTEXT"
    assert result["value"] == CURRENT_PB

@pytest.mark.asyncio
@patch('backend.agents.valuation.pb_ratio_agent.get_settings')
@patch('backend.agents.valuation.pb_ratio_agent.fetch_historical_price_series', new_callable=AsyncMock)
@patch('backend.agents.valuation.pb_ratio_agent.fetch_latest_bvps', new_callable=AsyncMock)
@patch('backend.agents.valuation.pb_ratio_agent.fetch_price_point', new_callable=AsyncMock)
async def test_pb_ratio_historical_insufficient_data(mock_fetch_price, mock_fetch_bvps, mock_fetch_hist, mock_get_settings, mock_settings, mock_get_redis_client):
    # Arrange
    mock_get_settings.return_value = mock_settings
    mock_fetch_price.return_value = {"latestPrice": CURRENT_PRICE}
    mock_fetch_bvps.return_value = {"bookValuePerShare": CURRENT_BVPS}
    # Create a series with few data points (e.g., less than MIN_HISTORICAL_DATA_POINTS if defined in agent)
    # Assuming agent has some minimum threshold, e.g. 10, for percentile calculation to be meaningful.
    # The agent currently checks for `historical_pb_series.empty` or `len(historical_pb_series) < 2` for std dev.
    # Percentile calculation itself doesn't have a strict minimum in scipy but might be less reliable.
    # For this test, let's provide a very short series.
    short_prices = pd.Series([90, 95, 100, 105, 110], index=pd.date_range(end=pd.Timestamp.today(), periods=5, freq='B'))
    mock_fetch_hist.return_value = short_prices

    # Act
    result = await pb_ratio_run(SYMBOL)

    # Assert
    # Depending on agent's handling of short series, it might still try to calculate or fall back.
    # Current agent logic will proceed if len >= 2.
    # For P/B = 2.0 (100/50), historical P/Bs: [1.8, 1.9, 2.0, 2.1, 2.2]
    # Percentile of 2.0 in [1.8, 1.9, 2.0, 2.1, 2.2] is 60.0 ( (2 + (3-2)/2) / 5 * 100 = (2.5/5)*100 = 50, no, (2+1/2)/5*100 = 50. kind='rank' (c_lt + c_eq/2)/n * 100 = (2+0.5)/5 * 100 = 50)
    # scipy.stats.percentileofscore([1.8,1.9,2.0,2.1,2.2], 2.0, kind='rank') is 60.0. ( (2 less, 1 equal). (2 + (1+2)/2) / 5 * 100? No.
    # Ah, it's ( (count_less) + (count_equal + 1)/2 if count_equal > 0 else 0 ) / N * 100 ? No.
    # It's (count_less + (count_equal)/2) / N * 100. So (2 + 1/2)/5 * 100 = 50.0. 
    # The test output for percentileofscore([1,2,3,4,5], 3, 'rank') is 60. (2 less, 1 equal). (2 + 1/2)/5 * 100 = 50.
    # The definition of 'rank' might be specific. For [1,2,3,4,5], score 3: (2 values < 3, 1 value == 3). (2 + (1+1)/2) / 5 * 100 = (2+1)/5 * 100 = 60. This is it.
    # So for [1.8, 1.9, 2.0, 2.1, 2.2], score 2.0: (2 values < 2.0, 1 value == 2.0). (2 + (1+1)/2) / 5 * 100 = 60.0.
    # With percentile 60.0 (25 <= 60 < 75), verdict should be FAIRLY_VALUED.
    assert result["verdict"] == "FAIRLY_VALUED_REL_HIST"
    assert result["value"] == CURRENT_PB # 2.0
    assert result["details"]["percentile_rank"] == 60.0
