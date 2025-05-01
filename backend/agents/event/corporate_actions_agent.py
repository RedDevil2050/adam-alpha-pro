import httpx
import datetime
from backend.utils.cache_utils import get_redis_client
from backend.agents.event.utils import tracker
# Import the specific data provider function
from backend.utils.data_provider import fetch_corporate_actions

agent_name = "corporate_actions_agent"


async def run(symbol: str) -> dict:
    redis_client = await get_redis_client() # Ensure redis client is awaited
    cache_key = f"{agent_name}:{symbol}"
    cached = await redis_client.get(cache_key)
    if cached:
        return cached

    # Fetch corporate actions using the data_provider function
    actions = []
    error_message = None
    try:
        # Use the imported fetch function
        # Assuming fetch_corporate_actions returns a list of action dicts or None/empty list
        actions_data = await fetch_corporate_actions(symbol)
        actions = actions_data if isinstance(actions_data, list) else []

    except Exception as e:
        error_message = str(e)
        # Return error structure if fetch fails
        return {
            "symbol": symbol,
            "verdict": "ERROR",
            "confidence": 0.0,
            "value": None,
            "details": {"error": error_message},
            "error": error_message, # Keep top-level error for consistency
            "agent_name": agent_name,
        }

    if not actions:
        result = {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": 0,
            "details": {},
            "agent_name": agent_name,
        }
    else:
        # Score based on number of actions
        count = len(actions)
        score = min(count / 5.0, 1.0) # Normalize score based on expected max actions
        verdict = (
            "ACTIVE" if score >= 0.6 else "MODERATE" if score >= 0.3 else "INACTIVE"
        )
        result = {
            "symbol": symbol,
            "verdict": verdict,
            "confidence": round(score, 4),
            "value": count,
            # Limit details to avoid large payloads, maybe just recent ones?
            "details": {"actions_count": count, "recent_actions": actions[:3]},
            "score": score,
            "agent_name": agent_name,
        }

    await redis_client.set(cache_key, result, ex=86400)
    tracker.update("event", agent_name, "implemented")
    return result
