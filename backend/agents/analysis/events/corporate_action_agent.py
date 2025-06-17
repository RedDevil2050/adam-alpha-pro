import httpx
from backend.utils.cache_utils import get_redis_client
from backend.agents.event.utils import tracker
from backend.agents.decorators import standard_agent_execution

agent_name = "corporate_action_agent"
AGENT_CATEGORY = "event"


@standard_agent_execution(
    agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=86400
)
async def run(symbol: str, agent_outputs: dict = None) -> dict:
    redis_client = await get_redis_client()
    cache_key = f"{agent_name}:{symbol}"
    cached = await redis_client.get(cache_key)
    if cached:
        return cached

    # Fetch corporate actions from an API or scrape data
    actions = []
    try:
        url = f"https://api.example.com/corporate-actions/{symbol}"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
        if resp.status_code == 200:
            actions = resp.json().get("actions", [])
    except Exception as e:
        return {
            "symbol": symbol,
            "verdict": "ERROR",
            "confidence": 0.0,
            "value": None,
            "details": {},
            "error": str(e),
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
        score = min(count / 5.0, 1.0)
        verdict = (
            "ACTIVE" if score >= 0.6 else "MODERATE" if score >= 0.3 else "INACTIVE"
        )
        result = {
            "symbol": symbol,
            "verdict": verdict,
            "confidence": round(score, 4),
            "value": count,
            "details": {"actions": actions},            "score": score,
            "agent_name": agent_name,
        }

    # Decorator handles caching and tracker update
    return result
