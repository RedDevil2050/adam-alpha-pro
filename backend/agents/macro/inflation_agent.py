from backend.utils.cache_utils import redis_client
from backend.utils.data_provider import fetch_inflation_rate
from backend.agents.macro.utils import tracker

agent_name = "inflation_agent"


async def run(symbol: str, country: str = "IND") -> dict:
    cache_key = f"{agent_name}:{country}"
    cached = await redis_client.get(cache_key)
    if cached:
        return cached

    value = await fetch_inflation_rate(country)
    if value is None:
        result = {
            "symbol": country,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {},
            "agent_name": agent_name,
        }
    else:
        # Normalize: >6% → high inflation (score=0), <2% → low inflation (score=1)
        if value >= 6:
            verdict, score = "HIGH", 0.0
        elif value <= 2:
            verdict, score = "LOW", 1.0
        else:
            score = (6 - value) / 4.0
            verdict = "MODERATE"
        result = {
            "symbol": country,
            "verdict": verdict,
            "confidence": round(score, 4),
            "value": round(value, 2),
            "details": {"inflation_pct": value},
            "score": score,
            "agent_name": agent_name,
        }

    await redis_client.set(cache_key, result, ex=86400)
    tracker.update("macro", agent_name, "implemented")
    return result
