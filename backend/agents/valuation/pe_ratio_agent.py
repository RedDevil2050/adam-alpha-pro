
from backend.utils.data_provider import fetch_price_point
from backend.utils.data_provider import fetch_eps
from backend.config.settings import settings
from loguru import logger

agent_name = "pe_ratio_agent"

async def run(symbol: str, agent_outputs: dict = {}) -> dict:
    try:
        price_data = await fetch_price_point(symbol)
        current_price = price_data.get("latestPrice", 0)

        eps = None
        if "eps_agent" in agent_outputs and agent_outputs["eps_agent"].get("value"):
            eps = float(agent_outputs["eps_agent"]["value"])
        else:
            eps = await fetch_eps(symbol)

        if not eps or eps <= 0 or not current_price or current_price <= 0:
            return {
                "symbol": symbol,
                "verdict": "NO_DATA",
                "confidence": 0.0,
                "value": None,
                "details": {
                    "current_price": current_price,
                    "eps": eps
                },
                "error": "Missing or invalid EPS/Price data",
                "agent_name": agent_name
            }

        pe_ratio = current_price / eps

        if pe_ratio < 10:
            verdict = "BUY"
        elif pe_ratio < 20:
            verdict = "HOLD"
        else:
            verdict = "AVOID"

        confidence = max(0.0, 100.0 - min(pe_ratio, 50.0) * 2)

        return {
            "symbol": symbol,
            "verdict": verdict,
            "confidence": confidence,
            "value": round(pe_ratio, 2),
            "details": {
                "current_price": current_price,
                "eps": eps
            },
            "error": None,
            "agent_name": agent_name
        }

    except Exception as e:
        logger.error(f"PE Ratio agent error for {symbol}: {e}")
        return {
            "symbol": symbol,
            "verdict": "ERROR",
            "confidence": 0.0,
            "value": None,
            "details": {},
            "error": str(e),
            "agent_name": agent_name
        }
