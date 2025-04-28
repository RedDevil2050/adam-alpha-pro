import pytest
import asyncio
import pandas as pd
# Import the run function directly
from backend.agents.market_regime_agent import run as market_regime_run 

@pytest.mark.asyncio
async def test_market_regime_agent(monkeypatch):
    symbol = "AAPL"

    # Mock the fetch_price_series function to return a pandas Series
    async def mock_fetch_price_series(symbol, years=None):
        # Need enough data for 200-day MA and 21-day slope calculation (~221 days)
        # Return a simple bullish trend for testing
        return pd.Series(range(100, 325)) 

    # Mock the VIX fetch as well
    async def mock_fetch_vix(symbol):
         return pd.Series([15]*250) # Mock VIX data

    # Monkeypatch the specific function used by the agent
    # The agent fetches "^VIX" separately, ensure that call is also mocked
    # We can use the same mock if the structure is compatible, or create a specific one
    # Let's refine the mock to handle both calls:
    
    # Store the original function if needed, though direct patching is often cleaner
    # original_fetch = market_regime_run.__globals__['fetch_price_series'] 
    
    async def combined_mock_fetch(sym, years=None):
        if sym == symbol:
            print(f"Mocking fetch_price_series for {sym}") # Debug print
            return await mock_fetch_price_series(sym, years)
        elif sym == "^VIX":
            print(f"Mocking fetch_price_series for {sym}") # Debug print
            return await mock_fetch_vix(sym)
        else:
            # Decide how to handle unexpected symbols: error, return None, or call original?
            # For isolated unit tests, raising an error might be best.
            raise ValueError(f"Unexpected symbol '{sym}' passed to mock fetch_price_series")
            # return await original_fetch(sym, years) # Call original for other symbols if needed

    monkeypatch.setattr("backend.agents.market_regime_agent.fetch_price_series", combined_mock_fetch)

    # Call the run function directly
    result = await market_regime_run(symbol)

    assert result["symbol"] == symbol
    # Based on the mock data (increasing price), expect Bullish
    assert result["verdict"] == "BULLISH" 
    assert "confidence" in result
    assert "value" in result # Slope value
    assert result.get("error") is None
    assert result.get("agent_name") == "MarketRegimeAgent"