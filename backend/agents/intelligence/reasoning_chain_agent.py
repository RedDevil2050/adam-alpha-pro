from backend.utils.cache_utils import redis_client
from backend.agents.intelligence.utils import tracker
from backend.config.settings import settings

agent_name = "reasoning_chain_agent"


async def run(symbol: str, agent_outputs: dict) -> dict:
    cache_key = f"{agent_name}:{symbol}"
    cached = await redis_client.get(cache_key)
    if cached:
        return cached

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

    await redis_client.set(cache_key, result, ex=None)
    tracker.update("intelligence", agent_name, "implemented")
    return result
