from backend.utils.cache_utils import get_redis_client
from backend.agents.intelligence.utils import tracker
import json # Import json
from backend.config.settings import settings

agent_name = "smart_explanation_agent"

async def run(symbol: str, agent_outputs: dict) -> dict:
    # Get Redis client when needed, don't initialize at module level
    redis_client = await get_redis_client()
    cache_key = f"{agent_name}:{symbol}"
    cached = await redis_client.get(cache_key)
    if cached:
        # Parse the JSON string from cache before returning
        return json.loads(cached)

    # Summarize top signals
    top = sorted(
        agent_outputs.items(), key=lambda x: x[1].get("confidence", 0), reverse=True
    )[:3]
    explanation = "; ".join([f"{k}→{v.get('verdict')}" for k, v in top])

    result = {
        "symbol": symbol,
        "verdict": "EXPLANATION",
        "confidence": 1.0,
        "value": explanation,
        "details": {"explanation": explanation},
        "score": 1.0,
        "agent_name": agent_name,
    }

    # Convert result to JSON string before caching
    await redis_client.set(cache_key, json.dumps(result), ex=None) # ex=None means no expiry, consider settings.agent_cache_ttl
    tracker.update("intelligence", agent_name, "implemented")
    return result
