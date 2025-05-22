import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from backend.agents.valuation.book_to_market_agent import run as btm_agent_run
from backend.config.settings import BookToMarketAgentSettings

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
        yield mock_func # Yield the function mock itself if needed, or the instance

# Mock settings for test isolation
@pytest.fixture
def mock_settings():
    settings_mock = MagicMock()
    # Create mock book_to_market settings with test values
    btm_settings = BookToMarketAgentSettings()
    btm_settings.HISTORICAL_YEARS = 5
    btm_settings.PERCENTILE_UNDERVALUED = 75.0  # High B/M (>75th percentile) is undervalued
    btm_settings.PERCENTILE_OVERVALUED = 25.0   # Low B/M (<25th percentile) is overvalued
    
    # Assign our mock btm_settings to the mock settings
    settings_mock.agent_settings.book_to_market = btm_settings
    return settings_mock

# Create a mock for historical price series with controlled distribution
def create_mock_price_series(mean_price=100.0, std_dev=10.0, days=500, book_value=80.0, current_price=100.0):
    """Create a mock price series that will produce a predictable B/M distribution"""
    # Generate dates
    end_date = datetime.now()
    dates = [end_date - timedelta(days=i) for i in range(days)]
    dates.reverse()  # oldest to newest
    
    # Generate prices with normal distribution
    np.random.seed(42)  # for reproducible tests
    prices = np.random.normal(mean_price, std_dev, days)
    prices = np.maximum(prices, 1.0)  # ensure positive prices
    
    # Create Series
    price_series = pd.Series(prices, index=dates)
    
    return price_series

@pytest.mark.asyncio
@patch('backend.agents.valuation.book_to_market_agent.get_settings')
async def test_btm_undervalued_with_historical_context(mock_get_settings, mock_settings, mock_get_redis_client): # Added mock_get_redis_client
    """Test B/M agent returns UNDERVALUED_REL_HIST when current B/M is high relative to history"""
    mock_get_settings.return_value = mock_settings
    
    # Setup: book value = 80, historical mean price = 100, current price = 80
    # This means current B/M = 1.0 (80/80), which should be high compared to history
    # Historical B/M mean would be ~0.8 (80/100)
    book_value = 80.0
    current_price = 80.0  # Low price → high B/M → undervalued
    
    # Create mocks with these values
    mock_fetch_price = AsyncMock(return_value=current_price)
    mock_fetch_book_value = AsyncMock(return_value=book_value)
    mock_hist_prices = create_mock_price_series(mean_price=100.0, std_dev=10.0, book_value=book_value, current_price=current_price)
    mock_fetch_hist_prices = AsyncMock(return_value=mock_hist_prices)
    
    # Apply mocks
    with patch('backend.agents.valuation.book_to_market_agent.fetch_price_point', mock_fetch_price), \
         patch('backend.agents.valuation.book_to_market_agent.fetch_book_value', mock_fetch_book_value), \
         patch('backend.agents.valuation.book_to_market_agent.fetch_historical_price_series', mock_fetch_hist_prices):
        
        # Execute agent
        result = await btm_agent_run("AAPL")
        
    # Assertions
    assert result["verdict"] == "UNDERVALUED_REL_HIST"
    assert result["confidence"] > 0.6  # Should have higher confidence for undervalued
    assert result["value"] == round(book_value / current_price, 4)  # B/M ratio
    assert "percentile_rank" in result["details"]
    assert result["details"]["percentile_rank"] > 75  # Should be above undervalued threshold
    assert result["details"]["config_used"]["percentile_undervalued"] == 75.0
    assert result["details"]["config_used"]["percentile_overvalued"] == 25.0

@pytest.mark.asyncio
@patch('backend.agents.valuation.book_to_market_agent.get_settings')
async def test_btm_overvalued_with_historical_context(mock_get_settings, mock_settings, mock_get_redis_client): # Added mock_get_redis_client
    """Test B/M agent returns OVERVALUED_REL_HIST when current B/M is low relative to history"""
    mock_get_settings.return_value = mock_settings
    
    # Setup: book value = 80, historical mean price = 100, current price = 160
    # This means current B/M = 0.5 (80/160), which should be low compared to history
    # Historical B/M mean would be ~0.8 (80/100)
    book_value = 80.0
    current_price = 160.0  # High price → low B/M → overvalued
    
    # Create mocks with these values
    mock_fetch_price = AsyncMock(return_value=current_price)
    mock_fetch_book_value = AsyncMock(return_value=book_value)
    mock_hist_prices = create_mock_price_series(mean_price=100.0, std_dev=10.0, book_value=book_value, current_price=current_price)
    mock_fetch_hist_prices = AsyncMock(return_value=mock_hist_prices)
    
    # Apply mocks
    with patch('backend.agents.valuation.book_to_market_agent.fetch_price_point', mock_fetch_price), \
         patch('backend.agents.valuation.book_to_market_agent.fetch_book_value', mock_fetch_book_value), \
         patch('backend.agents.valuation.book_to_market_agent.fetch_historical_price_series', mock_fetch_hist_prices):
        
        # Execute agent
        result = await btm_agent_run("AAPL")
        
    # Assertions
    assert result["verdict"] == "OVERVALUED_REL_HIST"
    assert result["confidence"] > 0.6  # Should have higher confidence for overvalued
    assert result["value"] == round(book_value / current_price, 4)  # B/M ratio
    assert "percentile_rank" in result["details"]
    assert result["details"]["percentile_rank"] < 25  # Should be below overvalued threshold
    assert result["details"]["config_used"]["percentile_undervalued"] == 75.0
    assert result["details"]["config_used"]["percentile_overvalued"] == 25.0

@pytest.mark.asyncio
@patch('backend.agents.valuation.book_to_market_agent.get_settings')
async def test_btm_fairly_valued_with_historical_context(mock_get_settings, mock_settings, mock_get_redis_client): # Added mock_get_redis_client
    """Test B/M agent returns FAIRLY_VALUED_REL_HIST when current B/M is close to historical mean"""
    mock_get_settings.return_value = mock_settings
    
    # Setup: book value = 80, historical mean price = 100, current price = 100
    # This means current B/M = 0.8 (80/100), which should be in the middle range
    book_value = 80.0
    current_price = 100.0  # Average price → mid-range B/M → fairly valued
    
    # Create mocks with these values
    mock_fetch_price = AsyncMock(return_value=current_price)
    mock_fetch_book_value = AsyncMock(return_value=book_value)
    mock_hist_prices = create_mock_price_series(mean_price=100.0, std_dev=10.0, book_value=book_value, current_price=current_price)
    mock_fetch_hist_prices = AsyncMock(return_value=mock_hist_prices)
    
    # Apply mocks
    with patch('backend.agents.valuation.book_to_market_agent.fetch_price_point', mock_fetch_price), \
         patch('backend.agents.valuation.book_to_market_agent.fetch_book_value', mock_fetch_book_value), \
         patch('backend.agents.valuation.book_to_market_agent.fetch_historical_price_series', mock_fetch_hist_prices):
        
        # Execute agent
        result = await btm_agent_run("AAPL")
        
    # Assertions
    assert result["verdict"] == "FAIRLY_VALUED_REL_HIST"
    assert result["confidence"] == 0.5  # Middle confidence for fairly valued
    assert result["value"] == round(book_value / current_price, 4)  # B/M ratio
    assert "percentile_rank" in result["details"]
    assert 25 < result["details"]["percentile_rank"] < 75  # Should be between thresholds

@pytest.mark.asyncio
@patch('backend.agents.valuation.book_to_market_agent.get_settings')
async def test_btm_negative_book_value(mock_get_settings, mock_settings, mock_get_redis_client): # Added mock_get_redis_client
    """Test B/M agent returns NEGATIVE_OR_ZERO_BV when book value is negative or zero"""
    mock_get_settings.return_value = mock_settings
    
    # Setup: negative book value
    book_value = -10.0
    current_price = 100.0
    
    # Create mocks with these values
    mock_fetch_price = AsyncMock(return_value=current_price)
    mock_fetch_book_value = AsyncMock(return_value=book_value)
    mock_hist_prices = create_mock_price_series(mean_price=100.0, std_dev=10.0, book_value=book_value, current_price=current_price)
    mock_fetch_hist_prices = AsyncMock(return_value=mock_hist_prices)
    
    # Apply mocks
    with patch('backend.agents.valuation.book_to_market_agent.fetch_price_point', mock_fetch_price), \
         patch('backend.agents.valuation.book_to_market_agent.fetch_book_value', mock_fetch_book_value), \
         patch('backend.agents.valuation.book_to_market_agent.fetch_historical_price_series', mock_fetch_hist_prices):
        
        # Execute agent
        result = await btm_agent_run("AAPL")
        
    # Assertions
    assert result["verdict"] == "NEGATIVE_OR_ZERO_BV"
    assert result["confidence"] == 0.7  # Fixed confidence for negative BV
    assert result["value"] == round(book_value / current_price, 4)  # B/M ratio (negative)

@pytest.mark.asyncio
@patch('backend.agents.valuation.book_to_market_agent.get_settings')
async def test_btm_missing_price_data(mock_get_settings, mock_settings, mock_get_redis_client): # Added mock_get_redis_client
    """Test B/M agent returns NO_DATA when price data is missing"""
    mock_get_settings.return_value = mock_settings
    
    # Setup: missing price
    book_value = 80.0
    current_price = None
    
    # Create mocks with these values
    mock_fetch_price = AsyncMock(return_value=current_price)
    mock_fetch_book_value = AsyncMock(return_value=book_value)
    
    # Apply mocks
    with patch('backend.agents.valuation.book_to_market_agent.fetch_price_point', mock_fetch_price), \
         patch('backend.agents.valuation.book_to_market_agent.fetch_book_value', mock_fetch_book_value):
        
        # Execute agent
        result = await btm_agent_run("AAPL")
        
    # Assertions
    assert result["verdict"] == "NO_DATA"
    assert result["confidence"] == 0.0
    assert result["value"] is None

@pytest.mark.asyncio
@patch('backend.agents.valuation.book_to_market_agent.get_settings')
async def test_btm_missing_book_value(mock_get_settings, mock_settings, mock_get_redis_client): # Added mock_get_redis_client
    """Test B/M agent returns NO_DATA when book value is missing"""
    mock_get_settings.return_value = mock_settings
    
    # Setup: missing book value
    book_value = None
    current_price = 100.0
    
    # Create mocks with these values
    mock_fetch_price = AsyncMock(return_value=current_price)
    mock_fetch_book_value = AsyncMock(return_value=book_value)
    
    # Apply mocks
    with patch('backend.agents.valuation.book_to_market_agent.fetch_price_point', mock_fetch_price), \
         patch('backend.agents.valuation.book_to_market_agent.fetch_book_value', mock_fetch_book_value):
        
        # Execute agent
        result = await btm_agent_run("AAPL")
        
    # Assertions
    assert result["verdict"] == "NO_DATA"
    assert result["confidence"] == 0.0
    assert result["value"] is None

@pytest.mark.asyncio
@patch('backend.agents.valuation.book_to_market_agent.get_settings')
async def test_btm_no_historical_context(mock_get_settings, mock_settings, mock_get_redis_client): # Added mock_get_redis_client
    """Test B/M agent handles missing historical price data gracefully"""
    mock_get_settings.return_value = mock_settings
    
    # Setup: valid current data but no historical data
    book_value = 80.0
    current_price = 100.0
    
    # Create mocks with these values
    mock_fetch_price = AsyncMock(return_value=current_price)
    mock_fetch_book_value = AsyncMock(return_value=book_value)
    mock_fetch_hist_prices = AsyncMock(return_value=None)  # No historical data
    
    # Apply mocks
    with patch('backend.agents.valuation.book_to_market_agent.fetch_price_point', mock_fetch_price), \
         patch('backend.agents.valuation.book_to_market_agent.fetch_book_value', mock_fetch_book_value), \
         patch('backend.agents.valuation.book_to_market_agent.fetch_historical_price_series', mock_fetch_hist_prices):
        
        # Execute agent
        result = await btm_agent_run("AAPL")
        
    # Assertions
    assert result["verdict"] == "NO_HISTORICAL_CONTEXT"
    assert result["confidence"] == 0.3  # Lower confidence due to missing historical context
    assert result["value"] == round(book_value / current_price, 4)  # B/M ratio
    assert result["details"]["percentile_rank"] is None
    assert result["details"]["z_score"] is None