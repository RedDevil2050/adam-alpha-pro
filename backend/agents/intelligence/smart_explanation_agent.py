from backend.utils.cache_utils import get_redis_client
from backend.agents.intelligence.utils import tracker
from backend.config.settings import settings

agent_name = "smart_explanation_agent"

redis_client = get_redis_client()

async def run(symbol: str, agent_outputs: dict) -> dict:
    cache_key = f"{agent_name}:{symbol}"
    cached = await redis_client.get(cache_key)
    if cached:
        return cached

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

    await redis_client.set(cache_key, result, ex=None)
    tracker.update("intelligence", agent_name, "implemented")
    return result
