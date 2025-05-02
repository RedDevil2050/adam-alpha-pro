import pytest
import pandas as pd
import numpy as np # Import numpy
from unittest.mock import AsyncMock, patch, MagicMock # Import patch and MagicMock
# Corrected import path and alias
from backend.agents.market.market_regime_agent import run as mr_run
from backend.config.settings import get_settings # Import settings

# Define agent_name if it's used elsewhere or for clarity
agent_name = "market_regime_agent"

@pytest.mark.asyncio
async def test_market_regime_agent(monkeypatch):
    # 1. Create longer mock data for a bullish scenario (250 days)
    dates = pd.to_datetime([pd.Timestamp('2025-05-01') - pd.Timedelta(days=x) for x in range(249, -1, -1)])
    # Simple increasing trend
    prices = np.linspace(100, 150, 250)
    mock_prices_df = pd.DataFrame({'Close': prices}, index=dates)

    # 2. Mock fetch_price_series to return the DataFrame regardless of symbol
    async def mock_fetch(*args, **kwargs):
        # Log the call for debugging if needed
        market_symbol = get_settings().data_provider.MARKET_INDEX_SYMBOL
        print(f"Mock fetch_price_series called with: args={args}, kwargs={kwargs}, market_symbol={market_symbol}")
        # Always return the bullish mock data during this test
        return mock_prices_df.copy()
        # Original conditional logic:
        # if args[0] == market_symbol:
        #     return mock_prices_df.copy() # Return a copy to avoid side effects
        # # Return empty DataFrame or raise error for other symbols if needed for stricter test
        # return pd.DataFrame()

    mock_fetch_async = AsyncMock(side_effect=mock_fetch)
    # Change the patch target to where the agent imports the function
    monkeypatch.setattr('backend.agents.market.market_regime_agent.fetch_price_series', mock_fetch_async)

    # Mock redis get/set using the correct patch target for the decorator
    mock_redis_instance = AsyncMock()
    mock_redis_instance.get.return_value = None # Simulate cache miss
    mock_redis_instance.set = AsyncMock()
    # Patch the get_redis_client function where the decorator imports it
    mock_get_redis = AsyncMock(return_value=mock_redis_instance)
    monkeypatch.setattr('backend.utils.cache_utils.get_redis_client', mock_get_redis)

    # Mock the tracker update via the decorator's import path
    mock_tracker_instance = AsyncMock()
    mock_tracker_instance.update_agent_status = AsyncMock()
    mock_get_tracker = MagicMock(return_value=mock_tracker_instance)
    monkeypatch.setattr('backend.agents.decorators.get_tracker', mock_get_tracker)

    # Mock settings to ensure the correct market index is used if necessary
    # This ensures the test uses the same index the mock expects
    # settings = get_settings()
    # market_symbol = settings.data_provider.MARKET_INDEX_SYMBOL

    # --- Remove Patch for pandas.DataFrame.rolling --- 
    # original_rolling = pd.DataFrame.rolling
    # def debug_rolling(self, *args, **kwargs):
    #     print(f"--- Rolling called on DataFrame ---")
    #     print(self.head())
    #     print("...")
    #     print(self.tail())
    #     print(f"--- Args: {args}, Kwargs: {kwargs} ---")
    #     return original_rolling(self, *args, **kwargs)
    # 
    # monkeypatch.setattr(pd.DataFrame, 'rolling', debug_rolling)
    # --- End Remove Patch ---

    # Run the agent - pass a dummy symbol, agent uses market index internally
    res = await mr_run('DUMMY_SYMBOL', agent_outputs={})

    # 3. Adjust assertions
    assert res['agent_name'] == agent_name
    assert res['symbol'] == 'DUMMY_SYMBOL' # Agent should return the original symbol
    # Add SMA details to the assertion message for better debugging
    assert res['verdict'] == 'BULL', f"Expected BULL, got {res['verdict']} with SMAs: short={res['details'].get('short_sma')}, long={res['details'].get('long_sma')}"
    assert 'details' in res
    assert 'market_regime' in res['details']
    assert res['details']['market_regime'] == 'BULL' # Check the specific detail key
    assert res['confidence'] == 0.7 # Check expected confidence for BULL
    assert res.get('error') is None # Ensure no error is reported

    # Verify mocks
    mock_get_redis.assert_awaited_once() # Check the factory function was awaited
    mock_redis_instance.get.assert_awaited_once() # Check get on the instance was awaited
    # Check if set was awaited (it should be if verdict is not ERROR/NO_DATA)
    if res['verdict'] not in ["ERROR", "NO_DATA", None]:
        mock_redis_instance.set.assert_awaited_once()
    else:
        mock_redis_instance.set.assert_not_awaited()

    # Verify fetch_price_series was called (at least once, for the market index)
    mock_fetch_async.assert_awaited()
    # More specific assertion: ensure it was called with the market index symbol
    market_symbol = get_settings().data_provider.MARKET_INDEX_SYMBOL
    mock_fetch_async.assert_any_await(market_symbol)

    # Verify tracker was called via the decorator
    mock_get_tracker.assert_called_once()
    mock_tracker_instance.update_agent_status.assert_awaited_once()