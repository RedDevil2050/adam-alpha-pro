import httpx
from backend.config.settings import settings
from backend.utils.cache_utils import redis_client
from backend.agents.sentiment.utils import tracker

agent_name = "news_volume_spike_agent"


async def run(symbol: str, window_hours: int = 24) -> dict:
    cache_key = f"{agent_name}:{symbol}:{window_hours}"
    # Cache check
    cached = await redis_client.get(cache_key)
    if cached:
        return cached

    # Fetch recent news count via NewsAPI
    api_key = settings.news_api_key
    url = "https://newsapi.org/v2/everything"
    params = {"q": symbol, "apiKey": api_key, "from": None, "pageSize": 100}
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params=params)
    count = 0
    if resp.status_code == 200:
        data = resp.json()
        count = len(data.get("articles", []))
    # Normalize volume: >50 articles => score 1.0, <10 => 0.0, else linear
    if count >= 50:
        score = 1.0
    elif count <= 10:
        score = 0.0
    else:
        score = (count - 10) / 40.0
    verdict = (
        "HIGH_VOLUME"
        if score >= 0.75
        else ("LOW_VOLUME" if score <= 0.25 else "MEDIUM_VOLUME")
    )
    result = {
        "symbol": symbol,
        "verdict": verdict,
        "confidence": round(score, 4),
        "value": count,
        "details": {},
        "score": score,
        "agent_name": agent_name,
    }

    # Cache & track
    await redis_client.set(cache_key, result, ex=3600)
    tracker.update("sentiment", agent_name, "implemented")
    return result
