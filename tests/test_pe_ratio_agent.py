import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest.mock import AsyncMock, patch
from backend.agents.valuation.pe_ratio_agent import run as pe_run

@pytest.mark.asyncio
@patch('backend.agents.decorators.get_redis_client')  # Add Redis mock
async def test_pe_ratio_agent(mock_get_redis, monkeypatch):
    # Mock the financial data provider with complete data
    async def mock_fetch_financial_data(symbol):
        return {
            'price': 200.00,
            'eps': 10.00,
            'pe_ratio': 20.00,  # Include direct PE ratio
            'sector': 'Technology',  # Sector for context
            'market_cap': 1000000000,  # Market cap for context
            'industry_pe': 25.00  # Industry average for comparison
        }
    monkeypatch.setattr('backend.utils.data_provider.fetch_financial_data', mock_fetch_financial_data)

    # Set up Redis mock instance
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get = AsyncMock(return_value=None)  # Simulate cache miss
    mock_redis_instance.set = AsyncMock()
    mock_get_redis.return_value = mock_redis_instance

    # Run the agent
    result = await pe_run('TCS')

    # Verify Redis operations
    mock_redis_instance.get.assert_awaited_once()
    mock_redis_instance.set.assert_awaited_once()

    # Verify results
    assert result['symbol'] == 'TCS'
    assert result['pe_ratio'] == pytest.approx(20.0, rel=1e-2)
    assert result['verdict'] == 'UNDERVALUED'  # PE ratio below industry average suggests undervalued
    assert 'confidence' in result
    assert isinstance(result['confidence'], float)
    assert 0 <= result['confidence'] <= 1.0
    assert 'details' in result
    assert 'industry_pe' in result['details']  # Should include comparison metrics in details