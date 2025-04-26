
from backend.agents.valuation.dcf_agent import run as dcf_run
from backend.agents.valuation.pe_ratio_agent import run as pe_run
from backend.agents.valuation.pb_ratio_agent import run as pb_run
from loguru import logger

agent_name = "intrinsic_composite_agent"

async def run(symbol: str, agent_outputs: dict = {}) -> dict:
    try:
        dcf = await dcf_run(symbol, agent_outputs)
        pe = await pe_run(symbol, agent_outputs)
        pb = await pb_run(symbol, agent_outputs)

        scores = []
        for result in [dcf, pe, pb]:
            if result["verdict"] not in {"ERROR", "NO_DATA"}:
                scores.append(result["confidence"])

        if not scores:
            return {
                "symbol": symbol,
                "verdict": "NO_DATA",
                "confidence": 0.0,
                "value": None,
                "details": {},
                "error": "No valid valuation signals",
                "agent_name": agent_name
            }

        avg_conf = sum(scores) / len(scores)
        verdict = "BUY" if avg_conf > 70 else "HOLD" if avg_conf > 40 else "AVOID"

        return {
            "symbol": symbol,
            "verdict": verdict,
            "confidence": avg_conf,
            "value": None,
            "details": {"dcf": dcf, "pe": pe, "pb": pb},
            "error": None,
            "agent_name": agent_name
        }

    except Exception as e:
        logger.error(f"Intrinsic composite error: {e}")
        return {
            "symbol": symbol,
            "verdict": "ERROR",
            "confidence": 0.0,
            "value": None,
            "details": {},
            "error": str(e),
            "agent_name": agent_name
        }
