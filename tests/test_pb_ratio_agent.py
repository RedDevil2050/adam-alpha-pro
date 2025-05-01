import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest.mock import AsyncMock, patch
from backend.agents.valuation.pb_ratio_agent import run as pb_run

@pytest.mark.asyncio
@patch('backend.agents.decorators.get_redis_client')  # Add Redis mock
async def test_pb_ratio_agent(mock_get_redis, monkeypatch):
    # Mock the financial data provider with complete data
    async def mock_fetch_financial_data(symbol):
        return {
            'price': 100.00,
            'book_value': 50.00,
            'pb_ratio': 2.00,  # Direct PB ratio
            'sector': 'Technology',  # Sector for context
            'market_cap': 1000000000,  # Market cap for context
            'industry_pb': 2.50,  # Industry average for comparison
            'total_assets': 2000000000,
            'total_liabilities': 1000000000
        }
    monkeypatch.setattr('backend.utils.data_provider.fetch_financial_data', mock_fetch_financial_data)

    # Set up Redis mock instance
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get = AsyncMock(return_value=None)  # Simulate cache miss
    mock_redis_instance.set = AsyncMock()
    mock_get_redis.return_value = mock_redis_instance

    # Run the agent
    result = await pb_run('TCS')

    # Verify Redis operations
    mock_redis_instance.get.assert_awaited_once()
    mock_redis_instance.set.assert_awaited_once()

    # Verify results
    assert result['symbol'] == 'TCS'
    assert result['pb_ratio'] == pytest.approx(2.0, rel=1e-2)
    assert result['verdict'] == 'UNDERVALUED'  # PB ratio below industry average suggests undervalued
    assert 'confidence' in result
    assert isinstance(result['confidence'], float)
    assert 0 <= result['confidence'] <= 1.0
    assert 'details' in result
    assert 'industry_pb' in result['details']  # Should include comparison metrics in details

@pytest.mark.asyncio
@patch('backend.agents.decorators.get_redis_client')
async def test_pb_ratio_overvalued(mock_get_redis, monkeypatch):
    # Mock data for overvalued case
    async def mock_fetch_financial_data(symbol):
        return {
            'price': 150.00,
            'book_value': 50.00,
            'pb_ratio': 3.00,  # Higher than industry average
            'sector': 'Technology',
            'market_cap': 1000000000,
            'industry_pb': 2.50,
            'total_assets': 2000000000,
            'total_liabilities': 1000000000
        }
    monkeypatch.setattr('backend.utils.data_provider.fetch_financial_data', mock_fetch_financial_data)

    # Set up Redis mock instance
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get = AsyncMock(return_value=None)
    mock_redis_instance.set = AsyncMock()
    mock_get_redis.return_value = mock_redis_instance

    # Run the agent
    result = await pb_run('TCS')

    # Verify results
    assert result['pb_ratio'] == pytest.approx(3.0, rel=1e-2)
    assert result['verdict'] == 'OVERVALUED'  # PB ratio above industry average
    assert 0 <= result['confidence'] <= 1.0