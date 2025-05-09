from backend.utils.cache_utils import get_redis_client
from backend.utils.data_provider import fetch_price_series, fetch_eps_data
import json # Import json
from backend.agents.intelligence.utils import tracker

agent_name = "ask_adam_agent"


async def run(symbol: str, question: str = "") -> dict:
    redis_client = await get_redis_client()  # Modified
    cache_key = f"{agent_name}:{symbol}:{question}"
    cached = await redis_client.get(cache_key)
    if cached:
        # Parse the JSON string from cache before returning
        return json.loads(cached)

    q = question.lower()
    if "price" in q:
        prices = await fetch_price_series(symbol, source_preference=["api", "scrape"])
        value = prices[-1] if prices else None
        answer = f"Latest price: {value}"
    elif "eps" in q:
        eps_ts = await fetch_eps_data(symbol)
        value = eps_ts[-1] if eps_ts else None
        answer = f"Latest EPS: {value}"
    else:
        answer = "I can provide price or EPS insights. Try asking specifically."

    result = {
        "symbol": symbol,
        "verdict": "INFO",
        "confidence": 1.0,
        "value": answer,
        "details": {"answer": answer},
        "score": 1.0,
        "agent_name": agent_name,
    }

    # Convert result to JSON string before caching
    await redis_client.set(cache_key, json.dumps(result), ex=None) # ex=None means no expiry, consider settings.agent_cache_ttl
    tracker.update("intelligence", agent_name, "implemented")
    return result
