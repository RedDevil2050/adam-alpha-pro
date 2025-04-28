from backend.utils.data_provider import fetch_price_point, fetch_sales_per_share
from loguru import logger

agent_name = "price_to_sales_agent"


async def run(symbol: str, agent_outputs: dict = {}) -> dict:
    try:
        price_data = await fetch_price_point(symbol)
        price = price_data.get("latestPrice", 0)

        sales = await fetch_sales_per_share(symbol)
        if not price or not sales or sales <= 0:
            return {
                "symbol": symbol,
                "verdict": "NO_DATA",
                "confidence": 0.0,
                "value": None,
                "details": {"price": price, "sales_per_share": sales},
                "error": "Missing or invalid sales data",
                "agent_name": agent_name,
            }

        ratio = price / sales
        verdict = "BUY" if ratio < 2 else "HOLD" if ratio <= 4 else "AVOID"
        confidence = max(0.0, 100.0 - ratio * 10)

        return {
            "symbol": symbol,
            "verdict": verdict,
            "confidence": confidence,
            "value": round(ratio, 2),
            "details": {"price": price, "sales_per_share": sales},
            "error": None,
            "agent_name": agent_name,
        }
    except Exception as e:
        logger.error(f"Price/Sales error: {e}")
        return {
            "symbol": symbol,
            "verdict": "ERROR",
            "confidence": 0.0,
            "value": None,
            "details": {},
            "error": str(e),
            "agent_name": agent_name,
        }
