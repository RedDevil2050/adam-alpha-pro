from backend.utils.data_provider import fetch_transcript
from textblob import TextBlob
from loguru import logger
from backend.utils.cache_utils import cache_data_provider

agent_name = "transcript_sentiment_agent"


@cache_data_provider(ttl=3600)
async def run(symbol: str, agent_outputs: dict = {}) -> dict:
    try:
        transcript = await fetch_transcript(symbol)
        if not transcript:
            return {
                "symbol": symbol,
                "verdict": "NO_DATA",
                "confidence": 0.0,
                "value": None,
                "details": {},
                "error": "No transcript",
                "agent_name": agent_name,
            }

        blob = TextBlob(transcript)
        score = blob.sentiment.polarity
        verdict = (
            "POSITIVE" if score > 0.3 else "NEGATIVE" if score < -0.3 else "NEUTRAL"
        )
        return {
            "symbol": symbol,
            "verdict": verdict,
            "confidence": round(abs(score) * 100, 2),
            "value": round(score, 3),
            "details": {"word_count": len(transcript.split())},
            "error": None,
            "agent_name": agent_name,
        }

    except Exception as e:
        logger.error(f"Transcript Sentiment error: {e}")
        return {
            "symbol": symbol,
            "verdict": "ERROR",
            "confidence": 0.0,
            "value": None,
            "details": {},
            "error": str(e),
            "agent_name": agent_name,
        }
