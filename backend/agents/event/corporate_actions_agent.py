import httpx
import datetime
from backend.utils.cache_utils import get_redis_client
from backend.agents.event.utils import tracker
from bs4 import BeautifulSoup

agent_name = "corporate_actions_agent"


async def run(symbol: str) -> dict:
    redis_client = get_redis_client()
    cache_key = f"{agent_name}:{symbol}"
    cached = await redis_client.get(cache_key)
    if cached:
        return cached

    # Scrape recent corporate actions from Trendlyne
    actions = []
    try:
        url = f"https://www.trendlyne.com/stock/{symbol}/corporate-announcements/"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
        soup = BeautifulSoup(resp.text, "html.parser")
        rows = soup.select(".announcement")
        for row in rows[:5]:
            date_str = row.select_one(".date").text.strip()
            desc = row.select_one(".title a").text.strip()
            date = datetime.datetime.strptime(date_str, "%d %b %Y").date()
            actions.append({"date": str(date), "description": desc})
    except Exception:
        pass

    if not actions:
        result = {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": 0,
            "details": {},
            "agent_name": agent_name,
        }
    else:
        # Score based on number of actions
        count = len(actions)
        score = min(count / 5.0, 1.0)
        verdict = (
            "ACTIVE" if score >= 0.6 else "MODERATE" if score >= 0.3 else "INACTIVE"
        )
        result = {
            "symbol": symbol,
            "verdict": verdict,
            "confidence": round(score, 4),
            "value": count,
            "details": {"actions": actions},
            "score": score,
            "agent_name": agent_name,
        }

    await redis_client.set(cache_key, result, ex=86400)
    tracker.update("event", agent_name, "implemented")
    return result
