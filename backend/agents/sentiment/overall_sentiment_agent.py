from backend.utils.cache_utils import redis_client
from backend.utils.data_provider import fetch_news, fetch_social_sentiment
from backend.agents.sentiment.utils import tracker

agent_name = "overall_sentiment_agent"

async def run(symbol: str) -> dict:
    cache_key = f"{agent_name}:{symbol}"
    cached = await redis_client.get(cache_key)
    if cached:
        return cached

    news_sent = await fetch_news_sentiment(symbol)
    social_sent = await fetch_social_sentiment(symbol)
    final = (news_sent + social_sent) / 2

    if final > 0.1:
        verdict="POSITIVE"
    elif final < -0.1:
        verdict="NEGATIVE"
    else:
        verdict="NEUTRAL"

    score = round((final + 1)/2,4)
    result = {"symbol": symbol, "verdict": verdict, "confidence":score,
              "value":final, "details":{}, "score":score, "agent_name":agent_name}

    await redis_client.set(cache_key, result, ex=None)
    tracker.update("sentiment", agent_name, "implemented")
    return result
