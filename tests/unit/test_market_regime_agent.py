import pytest
from backend.agents.market_regime_agent import MarketRegimeAgent

@pytest.mark.asyncio
async def test_market_regime_agent():
    agent = MarketRegimeAgent()
    symbol = "AAPL"

    # Mock the fetch_price_series function
    async def mock_fetch_price_series(symbol, start_date, end_date):
        return {"prices": [150, 152, 148, 155, 160]}

    agent.fetch_price_series = mock_fetch_price_series

    result = await agent._execute(symbol)

    assert result["symbol"] == symbol
    assert result["verdict"] in ["Bullish", "Bearish", "Neutral"]
    assert result["confidence"] > 0
    assert result["value"] is not None
    assert result["error"] is None