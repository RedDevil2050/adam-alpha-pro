
from backend.utils.data_provider import fetch_price_point, fetch_dividend
from loguru import logger

agent_name = "dividend_yield_agent"

async def run(symbol: str, agent_outputs: dict = {}) -> dict:
    try:
        price_data = await fetch_price_point(symbol)
        price = price_data.get("latestPrice", 0)
        dividend = await fetch_dividend(symbol)

        if not price or price <= 0 or not dividend:
            return {
                "symbol": symbol,
                "verdict": "NO_DATA",
                "confidence": 0.0,
                "value": None,
                "details": {"price": price, "dividend": dividend},
                "error": "Missing dividend data",
                "agent_name": agent_name
            }

        yield_percent = (dividend / price) * 100
        verdict = "BUY" if yield_percent > 3 else "HOLD" if yield_percent > 1 else "AVOID"
        confidence = min(100.0, yield_percent * 20)

        return {
            "symbol": symbol,
            "verdict": verdict,
            "confidence": confidence,
            "value": round(yield_percent, 2),
            "details": {"price": price, "dividend": dividend},
            "error": None,
            "agent_name": agent_name
        }
    except Exception as e:
        logger.error(f"Dividend Yield error: {e}")
        return {
            "symbol": symbol,
            "verdict": "ERROR",
            "confidence": 0.0,
            "value": None,
            "details": {},
            "error": str(e),
            "agent_name": agent_name
        }
