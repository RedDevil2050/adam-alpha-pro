
from backend.utils.data_provider import fetch_price_point, fetch_eps
from backend.config.settings import settings
from loguru import logger

agent_name = "reverse_dcf_agent"

async def run(symbol: str, agent_outputs: dict = {}) -> dict:
    try:
        price_data = await fetch_price_point(symbol)
        price = price_data.get("latestPrice", 0)
        eps = await fetch_eps(symbol)

        if not price or price <= 0 or not eps or eps <= 0:
            return {
                "symbol": symbol,
                "verdict": "NO_DATA",
                "confidence": 0.0,
                "value": None,
                "details": {"price": price, "eps": eps},
                "error": "Missing data",
                "agent_name": agent_name
            }

        implied_growth = ((price / eps / settings.DCF_DEFAULT_TERMINAL_PE) ** (1/settings.DCF_YEARS)) - 1
        verdict = "BUY" if implied_growth < 0.08 else "HOLD" if implied_growth <= 0.12 else "AVOID"
        confidence = max(0.0, 100.0 - implied_growth * 100)

        return {
            "symbol": symbol,
            "verdict": verdict,
            "confidence": confidence,
            "value": round(implied_growth * 100, 2),
            "details": {"price": price, "eps": eps},
            "error": None,
            "agent_name": agent_name
        }

    except Exception as e:
        logger.error(f"Reverse DCF error: {e}")
        return {
            "symbol": symbol,
            "verdict": "ERROR",
            "confidence": 0.0,
            "value": None,
            "details": {},
            "error": str(e),
            "agent_name": agent_name
        }
