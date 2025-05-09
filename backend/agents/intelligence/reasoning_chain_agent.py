from backend.utils.cache_utils import get_redis_client
from backend.agents.intelligence.utils import tracker
import json # Import json
from backend.config.settings import settings

agent_name = "reasoning_chain_agent"


async def run(symbol: str, agent_outputs: dict) -> dict:
    redis_client = get_redis_client()
    cache_key = f"{agent_name}:{symbol}"
    cached = await redis_client.get(cache_key)
    if cached:
        # Parse the JSON string from cache before returning
        return json.loads(cached)

    # Build chain-of-thought
    entries = [
        f"{k}:{v.get('verdict')}({v.get('confidence')})"
        for k, v in agent_outputs.items()
    ]
    reasoning = " -> ".join(entries)

    result = {
        "symbol": symbol,
        "verdict": "CHAIN",
        "confidence": 1.0,
        "value": reasoning,
        "details": {"chain": entries},
        "score": 1.0,
        "agent_name": agent_name,
    }

    # Convert result to JSON string before caching
    await redis_client.set(cache_key, json.dumps(result), ex=None) # ex=None means no expiry, consider settings.agent_cache_ttl
    tracker.update("intelligence", agent_name, "implemented")
    return result
