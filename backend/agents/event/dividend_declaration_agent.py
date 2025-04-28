import datetime
import pandas as pd
from backend.utils.cache_utils import redis_client
from backend.agents.event.utils import fetch_alpha_events, tracker

agent_name = "dividend_declaration_agent"


async def run(symbol: str) -> dict:
    cache_key = f"{agent_name}:{symbol}"
    cached = await redis_client.get(cache_key)
    if cached:
        return cached

    # 1) Fetch dividend data via AlphaVantage TIME_SERIES_DAILY_ADJUSTED
    data = await fetch_alpha_events(symbol, "TIME_SERIES_DAILY_ADJUSTED")
    ts = data.get("Time Series (Daily)", {})
    dates = []
    for date_str, vals in ts.items():
        if float(vals.get("7. dividend amount", 0)) > 0:
            dates.append(datetime.datetime.fromisoformat(date_str).date())
    dates.sort()
    next_date = None
    if dates:
        last_date = dates[-1]
        # Estimate period average
        if len(dates) > 1:
            periods = [(dates[i] - dates[i - 1]).days for i in range(1, len(dates))]
            avg_period = sum(periods) / len(periods)
            next_date = last_date + datetime.timedelta(days=int(avg_period))
        else:
            next_date = last_date

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
        score = max(0.0, min(1.0, (90 - days) / 90)) if days >= 0 else 0.0
        verdict = "UPCOMING" if days >= 0 else "PAST"
        result = {
            "symbol": symbol,
            "verdict": verdict,
            "confidence": round(score, 4),
            "value": str(next_date),
            "details": {"estimated_period_days": days},
            "score": score,
            "agent_name": agent_name,
        }

    await redis_client.set(cache_key, result, ex=86400)
    tracker.update("event", agent_name, "implemented")
    return result
