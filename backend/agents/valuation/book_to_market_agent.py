import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from backend.utils.data_provider import fetch_price_point, fetch_book_value
from backend.utils.cache_utils import redis_client
from backend.agents.valuation.utils import tracker
from loguru import logger

agent_name = "book_to_market_agent"

async def run(symbol: str, agent_outputs: dict = {}) -> dict:
    try:
        price = (await fetch_price_point(symbol)).get("latestPrice", 0)
        book = await fetch_book_value(symbol)

        if not price or not book or price <= 0:
            return {
                "symbol": symbol,
                "verdict": "NO_DATA",
                "confidence": 0.0,
                "value": None,
                "details": {"book": book, "price": price},
                "error": "Missing book or price",
                "agent_name": agent_name
            }

        btm = book / price
        verdict = "BUY" if btm > 1.0 else "HOLD" if btm > 0.5 else "AVOID"
        confidence = min(100.0, btm * 100)

        return {
            "symbol": symbol,
            "verdict": verdict,
            "confidence": confidence,
            "value": round(btm, 2),
            "details": {"book": book, "price": price},
            "error": None,
            "agent_name": agent_name
        }

    except Exception as e:
        logger.error(f"Book/Market agent error: {e}")
        return {
            "symbol": symbol,
            "verdict": "ERROR",
            "confidence": 0.0,
            "value": None,
            "details": {},
            "error": str(e),
            "agent_name": agent_name
        }
