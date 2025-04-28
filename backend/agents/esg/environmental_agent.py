from backend.utils.cache_utils import redis_client
from backend.agents.esg.utils import fetch_esg_breakdown, tracker

agent_name = "environmental_agent"


async def run(symbol: str) -> dict:
    cache_key = f"{agent_name}:{symbol}"
    # Cache check
    cached = await redis_client.get(cache_key)
    if cached:
        return cached

    # Fetch ESG breakdown
    scores = await fetch_esg_breakdown(symbol)
    value = scores.get("environmental")
    if value is None:
        result = {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {},
            "agent_name": agent_name,
        }
    else:
        # Normalize 0–100 to 0–1
        score = max(0.0, min(1.0, value / 100.0))
        # Verdict mapping
        if score >= 0.75:
            verdict = "EXCELLENT"
        elif score >= 0.5:
            verdict = "GOOD"
        elif score >= 0.25:
            verdict = "FAIR"
        else:
            verdict = "POOR"
        result = {
            "symbol": symbol,
            "verdict": verdict,
            "confidence": score,
            "value": value,
            "details": {"subscore": value},
            "score": score,
            "agent_name": agent_name,
        }

    # Cache & track
    await redis_client.set(cache_key, result, ex=3600)
    tracker.update("esg", agent_name, "implemented")
    return result
