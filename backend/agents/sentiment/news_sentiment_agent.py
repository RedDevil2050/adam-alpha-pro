import httpx
from backend.config.settings import settings
from backend.utils.cache_utils import redis_client
from backend.agents.sentiment.utils import analyzer, normalize_compound, tracker

agent_name = "news_sentiment_agent"

async def run(symbol: str) -> dict:
    cache_key = f"{agent_name}:{symbol}"
    # 1) Cache check
    cached = await redis_client.get(cache_key)
    if cached:
        return cached

    # 2) Fetch recent news headlines via NewsAPI
    api_key = settings.news_api_key
    url = "https://newsapi.org/v2/everything"
    params = {"q": symbol, "apiKey": api_key, "pageSize": 5, "sortBy": "publishedAt"}
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params=params)
    headlines = []
    if resp.status_code == 200:
        data = resp.json()
        for article in data.get("articles", []):
            title = article.get("title")
            if title:
                headlines.append(title)
    if not headlines:
        result = {"symbol": symbol, "verdict": "NO_DATA", "confidence": 0.0, "value": None, "details": {}, "agent_name": agent_name}
    else:
        # 3) Compute sentiment scores
        comp_scores = [analyzer.polarity_scores(h)["compound"] for h in headlines]
        avg_comp = sum(comp_scores) / len(comp_scores)
        score = normalize_compound(avg_comp)
        # 4) Verdict mapping
        if score >= 0.6:
            verdict = "POSITIVE"
        elif score <= 0.4:
            verdict = "NEGATIVE"
        else:
            verdict = "NEUTRAL"
        result = {
            "symbol": symbol,
            "verdict": verdict,
            "confidence": round(score, 4),
            "value": round(avg_comp, 4),
            "details": {"headlines_count": len(headlines)},
            "score": score,
            "agent_name": agent_name
        }

    # 5) Cache result for 1 hour and track progress
    await redis_client.set(cache_key, result, ex=3600)
    tracker.update("sentiment", agent_name, "implemented")
    return result
