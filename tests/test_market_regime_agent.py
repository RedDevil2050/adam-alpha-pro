import pytest
import pandas as pd # Import pandas
from unittest.mock import AsyncMock # Import AsyncMock
# Corrected import path
from backend.agents.market_regime_agent import run as mr_run 

@pytest.mark.asyncio
async def test_market_regime_agent(monkeypatch):
    # Mock market index data as a Pandas DataFrame
    mock_prices = pd.DataFrame({'Close': [100, 105, 110, 115]})
    # Use AsyncMock for the data provider function
    monkeypatch.setattr('backend.utils.data_provider.fetch_price_series', AsyncMock(return_value=mock_prices))
    
    # Mock redis get/set if the agent uses caching
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get.return_value = None # Simulate cache miss
    mock_redis_instance.set.return_value = None
    monkeypatch.setattr('backend.utils.cache_utils.get_redis_client', AsyncMock(return_value=mock_redis_instance))

    # Assuming the agent might take a symbol but uses a market index internally
    # Pass symbol and empty agent_outputs dict
    res = await mr_run('MARKET', agent_outputs={}) # Use a generic market symbol or check agent logic
    
    assert 'regime' in res
    assert res['regime'] in ['bullish', 'bearish', 'neutral']
    # Add more specific assertions based on the agent's logic and mock data if possible
    # For the increasing mock data, we might expect 'bullish'
    assert res['regime'] == 'bullish'

    # Verify cache was checked and set if applicable
    mock_redis_instance.get.assert_awaited_once()
    mock_redis_instance.set.assert_awaited_once()