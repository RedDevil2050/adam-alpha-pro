import datetime
from backend.utils.cache_utils import redis_client
from backend.agents.event.utils import fetch_alpha_events, tracker

agent_name = "share_buyback_agent"

async def run(symbol: str) -> dict:
    cache_key = f"{agent_name}:{symbol}"
    cached = await redis_client.get(cache_key)
    if cached:
        return cached

    # 1) API fetch hypothetical BUYBACK data
    data = await fetch_alpha_events(symbol, 'BUYBACK')
    date_str = data.get('buybackDate') or data.get('BuybackDate')
    buyback_date = None
    if date_str:
        try:
            buyback_date = datetime.datetime.fromisoformat(date_str).date()
        except Exception:
            pass

    # 2) Fallback scrape from Trendlyne
    if not buyback_date:
        try:
            import httpx
            from bs4 import BeautifulSoup
            url = f"https://www.trendlyne.com/stock/{symbol}/corporate-announcements/"
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url)
            soup = BeautifulSoup(resp.text, 'html.parser')
            elem = soup.find('th', string='Buyback Date')
            if elem:
                buyback_date = datetime.datetime.strptime(elem.find_next_sibling('td').text.strip(), '%d %b %Y').date()
        except Exception:
            pass

    if not buyback_date:
        result = {"symbol": symbol, "verdict": "NO_DATA", "confidence": 0.0, "value": None, "details": {}, "agent_name": agent_name}
    else:
        today = datetime.date.today()
        days = (buyback_date - today).days
        score = max(0.0, min(1.0, (60 - days) / 60)) if days >= 0 else 0.0
        verdict = "UPCOMING" if days >= 0 else "PAST"
        result = {
            "symbol": symbol,
            "verdict": verdict,
            "confidence": round(score, 4),
            "value": str(buyback_date),
            "details": {"days_to_event": days},
            "score": score,
            "agent_name": agent_name
        }

    await redis_client.set(cache_key, result, ex=86400)
    tracker.update("event", agent_name, "implemented")
    return result
