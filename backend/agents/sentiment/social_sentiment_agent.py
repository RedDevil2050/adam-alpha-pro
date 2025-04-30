import httpx
from backend.config.settings import settings
from backend.utils.cache_utils import get_redis_client
from backend.agents.sentiment.utils import analyzer, normalize_compound, tracker

agent_name = "social_sentiment_agent"


async def run(symbol: str) -> dict:
    cache_key = f"{agent_name}:{symbol}"
    redis_client = get_redis_client()
    # Cache check
    cached = await redis_client.get(cache_key)
    if cached:
        return cached

    # Fetch recent tweets using Twitter v2 API
    bearer = settings.twitter_bearer_token
    url = "https://api.twitter.com/2/tweets/search/recent"
    headers = {"Authorization": f"Bearer {bearer}"}
    params = {"query": symbol, "max_results": 5, "tweet.fields": "text"}
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, headers=headers, params=params)
    tweets = []
    if resp.status_code == 200:
        data = resp.json()
        for tweet in data.get("data", []):
            text = tweet.get("text")
            if text:
                tweets.append(text)
    if not tweets:
        result = {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {},
            "agent_name": agent_name,
        }
    else:
        comp_scores = [analyzer.polarity_scores(t)["compound"] for t in tweets]
        avg_comp = sum(comp_scores) / len(comp_scores)
        score = normalize_compound(avg_comp)
        verdict = (
            "POSITIVE" if score >= 0.6 else ("NEGATIVE" if score <= 0.4 else "NEUTRAL")
        )
        result = {
            "symbol": symbol,
            "verdict": verdict,
            "confidence": round(score, 4),
            "value": round(avg_comp, 4),
            "details": {"tweets_count": len(tweets)},
            "score": score,
            "agent_name": agent_name,
        }

    # Cache and update progress
    await redis_client.set(cache_key, result, ex=3600)
    tracker.update("sentiment", agent_name, "implemented")
    return result
