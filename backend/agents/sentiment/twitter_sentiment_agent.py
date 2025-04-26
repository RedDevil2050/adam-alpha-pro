
from backend.utils.data_provider import fetch_tweets
from textblob import TextBlob
from loguru import logger
from backend.utils.cache_utils import cache_data_provider

agent_name = "twitter_sentiment_agent"

@cache_data_provider(ttl=1800)
async def run(symbol: str, agent_outputs: dict = {}) -> dict:
    try:
        tweets = await fetch_tweets(symbol)
        if not tweets:
            return {
                "symbol": symbol,
                "verdict": "NO_DATA",
                "confidence": 0.0,
                "value": None,
                "details": {},
                "error": "No tweets available",
                "agent_name": agent_name
            }

        scores = [TextBlob(t).sentiment.polarity for t in tweets]
        avg = sum(scores) / len(scores)

        if avg > 0.3:
            verdict = "POSITIVE"
        elif avg < -0.3:
            verdict = "NEGATIVE"
        else:
            verdict = "NEUTRAL"

        return {
            "symbol": symbol,
            "verdict": verdict,
            "confidence": round(abs(avg) * 100, 2),
            "value": round(avg, 3),
            "details": {"num_tweets": len(tweets)},
            "error": None,
            "agent_name": agent_name
        }

    except Exception as e:
        logger.error(f"Twitter Sentiment error: {e}")
        return {
            "symbol": symbol,
            "verdict": "ERROR",
            "confidence": 0.0,
            "value": None,
            "details": {},
            "error": str(e),
            "agent_name": agent_name
        }
