import pytest
from backend.agents.esg.esg_score_agent import ESGScoreAgent

@pytest.mark.asyncio
async def test_esg_score_agent():
    agent = ESGScoreAgent()
    symbol = "AAPL"

    result = await agent._execute(symbol)

    assert result["symbol"] == symbol
    assert result["verdict"] == "CALCULATED"
    assert 0 <= result["confidence"] <= 1
    assert result["value"] == 85  # Placeholder ESG score
    assert result["error"] is None