
from backend.utils.data_provider import fetch_price_point, fetch_fcf_per_share
from loguru import logger

agent_name = "pfcf_ratio_agent"

async def run(symbol: str, agent_outputs: dict = {}) -> dict:
    try:
        price = (await fetch_price_point(symbol)).get("latestPrice", 0)
        fcf = await fetch_fcf_per_share(symbol)

        if not fcf or not price or fcf <= 0:
            return {
                "symbol": symbol,
                "verdict": "NO_DATA",
                "confidence": 0.0,
                "value": None,
                "details": {"fcf": fcf, "price": price},
                "error": "Invalid or missing FCF/Price",
                "agent_name": agent_name
            }

        pfcf = price / fcf
        verdict = "BUY" if pfcf < 12 else "HOLD" if pfcf < 20 else "AVOID"
        confidence = max(0.0, 100.0 - pfcf * 3)

        return {
            "symbol": symbol,
            "verdict": verdict,
            "confidence": confidence,
            "value": round(pfcf, 2),
            "details": {"fcf": fcf, "price": price},
            "error": None,
            "agent_name": agent_name
        }
    except Exception as e:
        logger.error(f"PFCF Ratio error: {e}")
        return {
            "symbol": symbol,
            "verdict": "ERROR",
            "confidence": 0.0,
            "value": None,
            "details": {},
            "error": str(e),
            "agent_name": agent_name
        }
