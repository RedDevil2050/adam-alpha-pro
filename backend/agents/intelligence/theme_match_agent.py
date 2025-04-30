import httpx
from backend.utils.cache_utils import get_redis_client
from backend.agents.intelligence.utils import tracker

agent_name = "theme_match_agent"
themes = ["Regulatory", "Earnings", "M&A", "Product", "Leadership"]


async def run(symbol: str) -> dict:
    cache_key = f"{agent_name}:{symbol}"
    redis_client = await get_redis_client()
    cached = await redis_client.get(cache_key)
    if cached:
        return cached

    # Fetch latest headlines
    from backend.utils.data_provider import fetch_news

    articles = await fetch_news(symbol)
    scores = {t: 0 for t in themes}
    for a in articles:
        for t in themes:
            if t.lower() in a.get("title", "").lower():
                scores[t] += 1

    # Choose top theme
    top = max(scores, key=scores.get) if scores else None
    score = scores.get(top, 0) / len(articles) if articles else 0.0

    result = {
        "symbol": symbol,
        "verdict": top or "NO_THEME",
        "confidence": round(score, 4),
        "value": scores,
        "details": scores,
        "score": score,
        "agent_name": agent_name,
    }

    await redis_client.set(cache_key, result, ex=None)
    tracker.update("intelligence", agent_name, "implemented")
    return result
