from nltk.sentiment.vader import SentimentIntensityAnalyzer
from backend.utils.cache_utils import redis_client
from backend.utils.data_provider import fetch_transcript
from backend.agents.management.utils import tracker

agent_name = "management_track_record_agent"


async def run(symbol: str) -> dict:
    cache_key = f"{agent_name}:{symbol}"
    cached = await redis_client.get(cache_key)
    if cached:
        return cached

    # Fetch latest earnings transcript
    text = await fetch_transcript(symbol)
    sid = SentimentIntensityAnalyzer()
    score = sid.polarity_scores(text).get("compound", 0.0)

    if score > 0.2:
        verdict = "STRONG_CONFIDENCE"
    elif score > 0.0:
        verdict = "NEUTRAL"
    else:
        verdict = "RISKY"

    result = {
        "symbol": symbol,
        "verdict": verdict,
        "confidence": round((score + 1) / 2, 4),
        "value": score,
        "details": {},
        "score": score,
        "agent_name": agent_name,
    }

    await redis_client.set(cache_key, result, ex=None)
    tracker.update("management", agent_name, "implemented")
    return result
