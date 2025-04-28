import httpx
from backend.utils.cache_utils import redis_client
from backend.agents.event.utils import tracker

agent_name = "earnings_calendar_agent"


async def run(symbol: str) -> dict:
    cache_key = f"{agent_name}:{symbol}"
    cached = await redis_client.get(cache_key)
    if cached:
        return cached

    # Fetch earnings calendar data from an API
    earnings_date = None
    try:
        url = f"https://api.example.com/earnings-calendar/{symbol}"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
        if resp.status_code == 200:
            earnings_date = resp.json().get("nextEarningsDate")
    except Exception as e:
        return {
            "symbol": symbol,
            "verdict": "ERROR",
            "confidence": 0.0,
            "value": None,
            "details": {},
            "error": str(e),
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
