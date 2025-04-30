import httpx
from backend.utils.cache_utils import get_redis_client
from backend.utils.data_provider import fetch_price_series
from backend.agents.intelligence.utils import tracker

agent_name = "target_price_agent"


async def run(symbol: str) -> dict:
    redis_client = get_redis_client()
    cache_key = f"{agent_name}:{symbol}"
    cached = await redis_client.get(cache_key)
    if cached:
        return cached

    # Fetch consensus using FinancialModelingPrep
    url = f"https://financialmodelingprep.com/api/v4/price-target?symbol={symbol}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
    data = resp.json()
    target = data[0].get("targetMean") if data else None

    # Current price
    prices = await fetch_price_series(symbol, source_preference=["api", "scrape"])
    current = prices[-1] if prices else None

    if target is None or current is None:
        result = {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {},
            "score": 0.0,
            "agent_name": agent_name,
        }
    else:
        diff = (target - current) / current
        score = min(max((diff + 0.2) / 0.4, 0), 1)
        if diff > 0.1:
            verdict = "BUY"
        elif diff < -0.1:
            verdict = "SELL"
        else:
            verdict = "HOLD"
        result = {
            "symbol": symbol,
            "verdict": verdict,
            "confidence": round(score, 4),
            "value": round(diff, 4),
            "details": {"target": target},
            "score": score,
            "agent_name": agent_name,
        }

    await redis_client.set(cache_key, result, ex=None)
    tracker.update("intelligence", agent_name, "implemented")
    return result
