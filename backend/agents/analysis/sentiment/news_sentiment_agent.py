import httpx
from backend.config.settings import settings
from backend.utils.cache_utils import get_redis_client
from backend.agents.analysis.sentiment.utils import analyzer, normalize_compound, tracker
from backend.agents.decorators import standard_agent_execution

agent_name = "news_sentiment_agent"
AGENT_CATEGORY = "sentiment"  # Define category for the decorator


@standard_agent_execution(
    agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=3600
)
async def run(symbol: str, agent_outputs: dict = None) -> dict:
    # Decorator handles cache check, so remove manual cache logic
    
    # Fetch recent news headlines via NewsAPI
    api_key = settings.news_api_key
    url = "https://newsapi.org/v2/everything"
    params = {"q": symbol, "apiKey": api_key, "pageSize": 5, "sortBy": "publishedAt"}
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params=params)
    headlines = []
    if resp.status_code == 200:
        # Await the json() coroutine
        data = await resp.json()
        for article in data.get("articles", []):
            title = article.get("title")
            if title:
                headlines.append(title)
    if not headlines:
        result = {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {},
            "agent_name": agent_name,
        }
    else:
        # Compute sentiment scores
        comp_scores = [analyzer.polarity_scores(h)["compound"] for h in headlines]
        avg_comp = sum(comp_scores) / len(comp_scores)
        score = normalize_compound(avg_comp)
        # Verdict mapping
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
            "agent_name": agent_name,
        }

    # Decorator handles caching and tracker update
    return result
