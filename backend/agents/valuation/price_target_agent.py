
from backend.utils.data_provider import fetch_eps, fetch_pe_target
from loguru import logger

agent_name = "price_target_agent"

async def run(symbol: str, agent_outputs: dict = {}) -> dict:
    try:
        eps = await fetch_eps(symbol)
        target_pe = await fetch_pe_target(symbol)

        if not eps or not target_pe:
            return {
                "symbol": symbol,
                "verdict": "NO_DATA",
                "confidence": 0.0,
                "value": None,
                "details": {"eps": eps, "target_pe": target_pe},
                "error": "Missing EPS or target PE",
                "agent_name": agent_name
            }

        target_price = eps * target_pe

        return {
            "symbol": symbol,
            "verdict": "TARGET_ESTIMATED",
            "confidence": 100.0,
            "value": round(target_price, 2),
            "details": {"eps": eps, "target_pe": target_pe},
            "error": None,
            "agent_name": agent_name
        }

    except Exception as e:
        logger.error(f"Price target agent error: {e}")
        return {
            "symbol": symbol,
            "verdict": "ERROR",
            "confidence": 0.0,
            "value": None,
            "details": {},
            "error": str(e),
            "agent_name": agent_name
        }
