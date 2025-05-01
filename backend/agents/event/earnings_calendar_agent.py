import httpx
from backend.utils.cache_utils import get_redis_client
from backend.agents.event.utils import tracker
# Import the specific data provider function
from backend.utils.data_provider import fetch_earnings_calendar

agent_name = "earnings_calendar_agent"


async def run(symbol: str) -> dict:
    cache_key = f"{agent_name}:{symbol}"
    redis_client = await get_redis_client() # Ensure redis client is awaited
    cached = await redis_client.get(cache_key)
    if cached:
        return cached

    # Fetch earnings calendar data using the data_provider function
    earnings_data = None
    error_message = None
    try:
        # Use the imported fetch function
        earnings_data = await fetch_earnings_calendar(symbol)
        # Assuming the provider returns a dict like {"nextEarningsDate": "YYYY-MM-DD"} or None/empty
        earnings_date = earnings_data.get("nextEarningsDate") if earnings_data else None

    except Exception as e:
        error_message = str(e)
        # Return error structure if fetch fails
        return {
            "symbol": symbol,
            "verdict": "ERROR",
            "confidence": 0.0,
            "value": None,
            "details": {"error": error_message},
            "error": error_message, # Keep top-level error for consistency
            "agent_name": agent_name,
        }

    if not earnings_date:
        result = {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {},
            "agent_name": agent_name,
        }
    else:
        result = {
            "symbol": symbol,
            "verdict": "UPCOMING",
            "confidence": 1.0,
            "value": earnings_date,
            "details": {"nextEarningsDate": earnings_date},
            "agent_name": agent_name,
        }

    await redis_client.set(cache_key, result, ex=86400)
    tracker.update("event", agent_name, "implemented")
    return result
