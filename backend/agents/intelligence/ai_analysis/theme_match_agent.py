import httpx
from backend.utils.cache_utils import get_redis_client
from backend.agents.decorators import standard_agent_execution
import json # Import json
from backend.agents.intelligence.ai_analysis.utils import tracker

agent_name = "theme_match_agent"
AGENT_CATEGORY = "intelligence"  # Define category for the decorator
themes = ["Regulatory", "Earnings", "M&A", "Product", "Leadership"]


@standard_agent_execution(
    agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=3600
)
async def run(symbol: str) -> dict:
    # Decorator handles cache check, so remove manual cache logic

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
        "agent_name": agent_name,        }

    # Decorator handles caching, so remove manual cache logic
    tracker.update("intelligence", agent_name, "implemented")
    return result
