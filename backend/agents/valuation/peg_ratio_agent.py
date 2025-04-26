
from backend.utils.data_provider import fetch_eps_growth_rate
from backend.agents.valuation.pe_ratio_agent import run as pe_run
from backend.config.settings import settings
from loguru import logger

agent_name = "peg_ratio_agent"

async def run(symbol: str, agent_outputs: dict = {}) -> dict:
    try:
        pe_result = await pe_run(symbol, agent_outputs)
        if pe_result["verdict"] in {"NO_DATA", "ERROR"} or not pe_result["value"]:
            return {**pe_result, "agent_name": agent_name}

        growth_rate = await fetch_eps_growth_rate(symbol)
        if not growth_rate or growth_rate <= 0:
            return {
                "symbol": symbol,
                "verdict": "NO_DATA",
                "confidence": 0.0,
                "value": None,
                "details": {"pe_ratio": pe_result["value"], "growth_rate": growth_rate},
                "error": "Missing or invalid EPS growth rate",
                "agent_name": agent_name
            }

        peg = pe_result["value"] / (growth_rate * 100)

        if peg < 1:
            verdict = "BUY"
        elif peg <= 2:
            verdict = "HOLD"
        else:
            verdict = "AVOID"

        return {
            "symbol": symbol,
            "verdict": verdict,
            "confidence": max(0.0, 100.0 - peg * 30),
            "value": round(peg, 2),
            "details": {"pe_ratio": pe_result["value"], "growth_rate": growth_rate},
            "error": None,
            "agent_name": agent_name
        }
    except Exception as e:
        logger.error(f"PEG Ratio agent error for {symbol}: {e}")
        return {
            "symbol": symbol,
            "verdict": "ERROR",
            "confidence": 0.0,
            "value": None,
            "details": {},
            "error": str(e),
            "agent_name": agent_name
        }
