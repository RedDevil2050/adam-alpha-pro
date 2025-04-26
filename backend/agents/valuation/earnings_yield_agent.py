
from backend.utils.data_provider import fetch_eps, fetch_price_point
from loguru import logger

agent_name = "earnings_yield_agent"

async def run(symbol: str, agent_outputs: dict = {}) -> dict:
    try:
        eps = await fetch_eps(symbol)
        price = (await fetch_price_point(symbol)).get("latestPrice", 0)

        if not eps or not price or price <= 0:
            return {
                "symbol": symbol,
                "verdict": "NO_DATA",
                "confidence": 0.0,
                "value": None,
                "details": {"eps": eps, "price": price},
                "error": "Missing EPS or price",
                "agent_name": agent_name
            }

        yield_pct = (eps / price) * 100
        verdict = "BUY" if yield_pct > 8 else "HOLD" if yield_pct > 5 else "AVOID"
        confidence = min(100.0, yield_pct * 10)

        return {
            "symbol": symbol,
            "verdict": verdict,
            "confidence": confidence,
            "value": round(yield_pct, 2),
            "details": {"eps": eps, "price": price},
            "error": None,
            "agent_name": agent_name
        }

    except Exception as e:
        logger.error(f"Earnings Yield agent error: {e}")
        return {
            "symbol": symbol,
            "verdict": "ERROR",
            "confidence": 0.0,
            "value": None,
            "details": {},
            "error": str(e),
            "agent_name": agent_name
        }
