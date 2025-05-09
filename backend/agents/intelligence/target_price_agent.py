import httpx
from backend.utils.cache_utils import get_redis_client
from backend.utils.data_provider import fetch_price_series
from backend.agents.intelligence.utils import tracker
from loguru import logger  # Add logger

agent_name = "target_price_agent"


async def run(symbol: str) -> dict:
    redis_client = await get_redis_client()  # Modified
    cache_key = f"{agent_name}:{symbol}"
    cached = await redis_client.get(cache_key)
    if cached:
        return cached

    # Fetch consensus using FinancialModelingPrep
    url = f"https://financialmodelingprep.com/api/v4/price-target?symbol={symbol}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
    
    data = None
    try:
        if resp.status_code == 200:
            data = resp.json()
        else:
            logger.warning(f"FMP API request for {symbol} failed with status {resp.status_code}: {await resp.text()}")
    except Exception as e:
        logger.error(f"Error decoding FMP API response for {symbol}: {e}")

    target = None
    if isinstance(data, list) and data:
        if isinstance(data[0], dict):
            target = data[0].get("targetMean")
        else:
            logger.warning(f"Expected list of dicts from FMP API for {symbol}, but first element is not a dict: {data[0]}")
    elif data:  # If data is not None/empty but also not a list (e.g. a dict error message from API)
        logger.warning(f"Expected list from FMP API for {symbol}, but got: {type(data)} - {str(data)[:200]}")

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
