import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest.mock import AsyncMock, patch
from backend.agents.valuation.eps_agent import run

@pytest.mark.asyncio
@patch('backend.agents.decorators.get_redis_client')  # Add Redis mock
async def test_eps_agent(mock_get_redis, monkeypatch):
    # Mock Alpha Vantage data with all potentially needed fields
    async def fake_alpha(endpoint, params):
        return {
            'EPS': '10.5',              # Basic EPS value
            'ReportedEPS': '10.5',      # Alternative field name
            'PERatio': '15.5',          # Related metrics that might be used
            'PEGRatio': '1.2',
            'MarketCap': '1000000000',
            'PriceToBookRatio': '2.5'
        }
    monkeypatch.setattr('backend.utils.data_provider.fetch_alpha_vantage', fake_alpha)

    # Set up Redis mock instance
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get = AsyncMock(return_value=None)  # Simulate cache miss
    mock_redis_instance.set = AsyncMock()
    mock_get_redis.return_value = mock_redis_instance

    # Run the agent
    result = await run('TEST')

    # Verify Redis operations
    mock_redis_instance.get.assert_awaited_once()
    mock_redis_instance.set.assert_awaited_once()

    # Verify results
    assert result['symbol'] == 'TEST'
    assert result['eps'] == 10.5  # Should be converted to float
    assert result['verdict'] in ['BUY', 'HOLD', 'SELL']  # Allow all valid verdicts
    assert 'confidence' in result
    assert isinstance(result['confidence'], float)
    assert 0 <= result['confidence'] <= 1.0
    assert 'details' in result