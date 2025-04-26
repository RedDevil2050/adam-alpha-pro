
import pytest
import asyncio
from backend.agents.technical.macd_agent import run

@pytest.mark.asyncio
async def test_macd_agent_schema():
    symbol = "INFY"
    result = await run(symbol)

    assert isinstance(result, dict)
    assert "symbol" in result
    assert "verdict" in result
    assert "confidence" in result
    assert "value" in result
    assert "details" in result
    assert "agent_name" in result
    assert result["verdict"] in {"BULLISH", "BEARISH", "NEUTRAL", "NO_DATA", "ERROR"}
    assert 0.0 <= result["confidence"] <= 100.0
    if result["value"] is not None:
        assert isinstance(result["value"], (int, float))
