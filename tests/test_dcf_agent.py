
import pytest
import asyncio
from backend.agents.valuation.dcf_agent import run

@pytest.mark.asyncio
async def test_dcf_agent_standard_output():
    symbol = "TCS"
    dummy_outputs = {
        "eps_agent": {"value": 80.0}
    }
    result = await run(symbol, dummy_outputs)

    assert isinstance(result, dict)
    assert "symbol" in result
    assert "verdict" in result
    assert "confidence" in result
    assert "value" in result
    assert "details" in result
    assert "agent_name" in result
    assert result["verdict"] in {"BUY", "HOLD", "AVOID", "NO_DATA", "ERROR"}
    assert 0.0 <= result["confidence"] <= 100.0
    if result["value"] is not None:
        assert isinstance(result["value"], float)
