import asyncio
from backend.utils.cache_utils import get_redis_client
from backend.config.settings import settings
from backend.agents.intelligence.utils import tracker
import importlib
import json # Import json

agent_name = "peer_compare_agent"


async def run(symbol: str) -> dict:
    redis_client = await get_redis_client()
    cache_key = f"{agent_name}:{symbol}"
    cached = await redis_client.get(cache_key)
    if cached:
        # Parse the JSON string from cache before returning
        return json.loads(cached)

    # Fetch PE ratio
    pe_mod = importlib.import_module("backend.agents.valuation.pe_ratio_agent")
    pe_res = await pe_mod.run(symbol)
    pe = pe_res.get("value")
    # Compare to sector average in settings
    sector_avg = settings.sector_pe_averages.get(symbol, None)
    if pe is None or sector_avg is None:
        result = {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {},
            "agent_name": agent_name,
        }
    else:
        diff = pe - sector_avg
        score = max(0.0, min(1.0, (sector_avg - diff) / sector_avg))
        verdict = "UNDERVALUED" if diff < 0 else "OVERVALUED"
        result = {
            "symbol": symbol,
            "verdict": verdict,
            "confidence": round(score, 4),
            "value": round(diff, 4),
            "details": {"pe": pe, "sector_avg": sector_avg},
            "score": score,
            "agent_name": agent_name,
        }

    # Convert result to JSON string before caching
    await redis_client.set(cache_key, json.dumps(result), ex=3600) # ex=settings.agent_cache_ttl would be better
    tracker.update("intelligence", agent_name, "implemented")
    return result
