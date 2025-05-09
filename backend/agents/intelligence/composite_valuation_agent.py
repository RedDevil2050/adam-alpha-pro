import pkgutil
import importlib
from backend.utils.cache_utils import get_redis_client
from backend.utils.data_provider import fetch_price_series
import json # Import json
from backend.agents.intelligence.utils import tracker

agent_name = "composite_valuation_agent"


async def run(symbol: str) -> dict:
    redis_client = await get_redis_client()
    cache_key = f"{agent_name}:{symbol}"
    cached = await redis_client.get(cache_key)
    if cached:
        # Parse the JSON string from cache before returning
        return json.loads(cached)

    # Dummy fetch to ensure data load
    _ = await fetch_price_series(symbol, source_preference=["api", "scrape"])

    scores = []
    pkg = importlib.import_module("backend.agents.valuation")
    for _, fullname, _ in pkgutil.walk_packages(
        path=pkg.__path__, prefix="backend.agents.valuation."
    ):
        if fullname.endswith(("utils", "__init__", "base")):
            continue
        mod = importlib.import_module(fullname)
        res = await mod.run(symbol)
        scores.append(res.get("score", 0.0))

    avg = sum(scores) / len(scores) if scores else 0.0
    verdict = (
        "STRONG_BUY"
        if avg >= 0.7
        else "BUY" if avg >= 0.5 else "HOLD" if avg >= 0.3 else "AVOID"
    )

    result = {
        "symbol": symbol,
        "verdict": verdict,
        "confidence": round(avg, 4),
        "value": avg,
        "details": {"scores": scores},
        "score": avg,
        "agent_name": agent_name,
    }

    # Convert result to JSON string before caching
    await redis_client.set(cache_key, json.dumps(result), ex=None) # ex=None means no expiry, consider settings.agent_cache_ttl
    tracker.update("intelligence", agent_name, "implemented")
    return result
