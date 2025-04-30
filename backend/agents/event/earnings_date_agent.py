import datetime
from backend.utils.cache_utils import get_redis_client
from backend.agents.event.utils import fetch_alpha_events, tracker

agent_name = "earnings_date_agent"


async def run(symbol: str) -> dict:
    redis_client = get_redis_client()
    cache_key = f"{agent_name}:{symbol}"
    cached = await redis_client.get(cache_key)
    if cached:
        return cached

    # 1) API fetch next earnings date
    data = await fetch_alpha_events(symbol, "EARNINGS")
    next_date_str = data.get("symbol", {}).get("NextEarningsDate") or data.get(
        "NextEarningsDate"
    )
    next_date = None
    if next_date_str:
        try:
            next_date = datetime.datetime.fromisoformat(next_date_str).date()
        except Exception:
            pass

    # 2) Fallback: scrape from Trendlyne
    if not next_date:
        try:
            import httpx
            from bs4 import BeautifulSoup

            url = f"https://www.trendlyne.com/stock/{symbol}/corporate-announcements/"
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url)
            soup = BeautifulSoup(resp.text, "html.parser")
            elem = soup.select_one(".announcement .date")
            if elem:
                next_date = datetime.datetime.strptime(
                    elem.text.strip(), "%d %b %Y"
                ).date()
        except Exception:
            pass

    if not next_date:
        result = {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {},
            "agent_name": agent_name,
        }
    else:
        today = datetime.date.today()
        days = (next_date - today).days
        score = max(0.0, min(1.0, (30 - days) / 30)) if days >= 0 else 0.0
        verdict = "UPCOMING" if days >= 0 else "PAST"
        result = {
            "symbol": symbol,
            "verdict": verdict,
            "confidence": round(score, 4),
            "value": str(next_date),
            "details": {"days_to_event": days},
            "score": score,
            "agent_name": agent_name,
        }

    await redis_client.set(cache_key, result, ex=86400)
    tracker.update("event", agent_name, "implemented")
    return result
