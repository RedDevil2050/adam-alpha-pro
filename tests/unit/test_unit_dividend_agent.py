import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from backend.agents.dividend_agent import DividendAgent

@pytest.mark.asyncio
@patch("backend.agents.dividend_agent.fetch_eps_data", new_callable=AsyncMock)
async def test_dividend_agent(mock_fetch_eps_data):
    mock_fetch_eps_data.return_value = {"dividend_yield": 0.03, "price": 150.0}

    # Create mock dependencies required by AgentBase
    mock_settings = MagicMock()
    mock_logger = MagicMock()
    mock_cache_client = MagicMock()
    mock_data_provider = MagicMock()
    mock_market_context_provider = MagicMock()

    # Create the agent with all required parameters
    agent = DividendAgent(
        name="test_dividend_agent",
        settings=mock_settings,
        logger=mock_logger,
        cache_client=mock_cache_client,
        data_provider=mock_data_provider,
        market_context_provider=mock_market_context_provider
    )
    
    symbol = "AAPL"

    result = await agent._execute(symbol)

    assert result["symbol"] == symbol
    assert result["verdict"] in ["BUY", "HOLD"]
    assert result["confidence"] > 0
    assert result["value"] == 0.03
    assert result["error"] is None

    # Verify that the mock is being called
    mock_fetch_eps_data.assert_called_once_with(symbol)