import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from backend.agents.valuation.price_to_sales_agent import run
from backend.utils.data_provider import fetch_alpha_vantage, fetch_iex

@pytest.mark.asyncio
@patch('backend.utils.cache_utils.get_redis_client') # Patch redis
@patch('backend.agents.valuation.price_to_sales_agent.fetch_company_info') # Patch company info fetch where used
@patch('backend.agents.valuation.price_to_sales_agent.fetch_price_point') # Patch price fetch where used
async def test_price_to_sales_agent(mock_fetch_price, mock_fetch_info, mock_get_redis, monkeypatch): # Order matches patches
    # Mock fetch_price_point to return a dict with 'price'
    mock_fetch_price.return_value = {'price': 10.0}
    # Mock fetch_company_info to return required fields
    mock_fetch_info.return_value = {
        'RevenueTTM': '1000',
        'SharesOutstanding': '100' # MarketCap / Price = 5000 / 10 = 500? Let's use explicit shares
    }

    # Mock Redis
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get.return_value = None # Cache miss
    mock_redis_instance.set = AsyncMock()
    mock_get_redis.return_value = mock_redis_instance

    # Expected calculations:
    # Sales Per Share = RevenueTTM / SharesOutstanding = 1000 / 100 = 10.0
    # P/S Ratio = Price / Sales Per Share = 10.0 / 10.0 = 1.0

    result = await run('TEST')

    # Assertions
    assert result['symbol'] == 'TEST'
    assert 'value' in result # Value holds the P/S ratio
    assert result['value'] == pytest.approx(1.0)
    assert 'details' in result
    assert 'price_to_sales_ratio' in result['details']
    assert result['details']['price_to_sales_ratio'] == pytest.approx(1.0)
    assert result['verdict'] == 'MODERATE_PS' # P/S = 1.0 falls into MODERATE
    assert result.get('error') is None

    # Verify mocks
    mock_fetch_price.assert_awaited_once_with('TEST')
    mock_fetch_info.assert_awaited_once_with('TEST')
    mock_redis_instance.get.assert_awaited_once()
    mock_redis_instance.set.assert_awaited_once()