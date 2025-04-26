
from backend.utils.data_provider import fetch_eps
from loguru import logger

agent_name = "eps_agent"

async def run(symbol: str, agent_outputs: dict = {}) -> dict:
    try:
        eps = await fetch_eps(symbol)
        if not eps or eps <= 0:
            return {
                "symbol": symbol,
                "verdict": "NO_DATA",
                "confidence": 0.0,
                "value": None,
                "details": {"eps": eps},
                "error": "Invalid EPS",
                "agent_name": agent_name
            }

        return {
            "symbol": symbol,
            "verdict": "VALID",
            "confidence": 100.0,
            "value": round(eps, 2),
            "details": {"eps": eps},
            "error": None,
            "agent_name": agent_name
        }

    except Exception as e:
        logger.error(f"EPS fetch error: {e}")
        return {
            "symbol": symbol,
            "verdict": "ERROR",
            "confidence": 0.0,
            "value": None,
            "details": {},
            "error": str(e),
            "agent_name": agent_name
        }
