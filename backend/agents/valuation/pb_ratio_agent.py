
from backend.utils.data_provider import fetch_price_point
from backend.utils.data_provider import fetch_book_value
from backend.config.settings import settings
from loguru import logger

agent_name = "pb_ratio_agent"

async def run(symbol: str, agent_outputs: dict = {}) -> dict:
    try:
        price_data = await fetch_price_point(symbol)
        current_price = price_data.get("latestPrice", 0)

        book_value = None
        if "book_value_agent" in agent_outputs and agent_outputs["book_value_agent"].get("value"):
            book_value = float(agent_outputs["book_value_agent"]["value"])
        else:
            book_value = await fetch_book_value(symbol)

        if not book_value or book_value <= 0 or not current_price or current_price <= 0:
            return {
                "symbol": symbol,
                "verdict": "NO_DATA",
                "confidence": 0.0,
                "value": None,
                "details": {
                    "current_price": current_price,
                    "book_value": book_value
                },
                "error": "Missing or invalid Book Value/Price data",
                "agent_name": agent_name
            }

        pb_ratio = current_price / book_value

        if pb_ratio < 1:
            verdict = "BUY"
        elif pb_ratio <= 3:
            verdict = "HOLD"
        else:
            verdict = "AVOID"

        confidence = max(0.0, 100.0 - min(pb_ratio, 10.0) * 10)

        return {
            "symbol": symbol,
            "verdict": verdict,
            "confidence": confidence,
            "value": round(pb_ratio, 2),
            "details": {
                "current_price": current_price,
                "book_value": book_value
            },
            "error": None,
            "agent_name": agent_name
        }

    except Exception as e:
        logger.error(f"PB Ratio agent error for {symbol}: {e}")
        return {
            "symbol": symbol,
            "verdict": "ERROR",
            "confidence": 0.0,
            "value": None,
            "details": {},
            "error": str(e),
            "agent_name": agent_name
        }
