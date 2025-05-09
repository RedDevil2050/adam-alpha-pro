import pandas as pd
import numpy as np
import json
from backend.utils.data_provider import fetch_price_series, fetch_eps_data
from backend.agents.event.earnings_calendar_agent import run as earnings_run
from backend.agents.event.corporate_actions_agent import run as corp_run
from backend.utils.cache_utils import get_redis_client
from backend.config.settings import settings
from backend.agents.automation.utils import tracker

agent_name = "alert_engine_agent"


async def run(symbol: str, agent_outputs: dict = {}) -> dict:
    redis_client = await get_redis_client()
    cache_key = f"{agent_name}:{symbol}"
    cached = await redis_client.get(cache_key)
    if cached:
        # Parse the JSON string from cache before returning
        return json.loads(cached)

    # 1) Fetch price series (60d) and compute 50-day MA
    prices = await fetch_price_series(symbol, source_preference=["api", "scrape"])
    
    price_series_1d = None
    if prices is not None:
        if isinstance(prices, pd.Series):
            price_series_1d = prices
        elif isinstance(prices, np.ndarray) and prices.ndim == 1:
            price_series_1d = pd.Series(prices)
        elif isinstance(prices, np.ndarray) and prices.ndim > 1:
            # Assuming close price is at a specific column, e.g., index 3 for OHLCV
            if prices.shape[1] > 3: # Ensure the column exists
                price_series_1d = pd.Series(prices[:, 3])
        elif isinstance(prices, list): # Basic list handling
             price_series_1d = pd.Series(prices)

    ma50 = None
    current_price = None
    if price_series_1d is not None and not price_series_1d.empty:
        current_price = price_series_1d.iloc[-1]
        ma50 = (price_series_1d.rolling(window=50).mean().iloc[-1]
                if len(price_series_1d) >= 50 else price_series_1d.mean())
 
    # 2) Fetch EPS time series, compute QoQ growth
    eps_ts = await fetch_eps_data(symbol)
    eps_growth = None
    if eps_ts and len(eps_ts) >= 2:
        eps_growth = (
            (eps_ts[-1] - eps_ts[-2]) / abs(eps_ts[-2]) if eps_ts[-2] != 0 else None
        )

    # 3) Upcoming earnings days to event
    earn_out = await earnings_run(symbol)
    days_to_earn = earn_out.get("details", {}).get("days_to_event")

    # 4) Corporate actions count
    corp_out = await corp_run(symbol)
    acts = corp_out.get("details", {}).get("actions", [])

    # 5) Build alerts
    alerts = []
    if current_price is not None and ma50 is not None and current_price > ma50:
        alerts.append("Above 50DMA")
    if eps_growth is not None and eps_growth > 0.1:
        alerts.append("EPS QoQ >10%")
    if days_to_earn is not None and days_to_earn <= 7:
        alerts.append("Earnings within 7d")
    if acts:
        alerts.append("Corporate Actions")

    # 6) Verdict and confidence
    verdict = "ALERT" if alerts else "NO_ALERT"
    confidence = min(len(alerts) / 4, 1.0)

    result = {
        "symbol": symbol,
        "verdict": verdict,
        "confidence": round(confidence, 4),
        "value": len(alerts),
        "details": {
            "alerts": alerts, # Ensure ma50 is not None before rounding
            "ma50": round(ma50, 2) if ma50 is not None else None,
            "eps_growth": eps_growth,
            "earnings_in": days_to_earn,
        },
        "score": confidence,
        "agent_name": agent_name,
    }

    # Convert result to JSON string before caching
    await redis_client.set(cache_key, json.dumps(result), ex=settings.agent_cache_ttl)
    tracker.update("automation", agent_name, "implemented")
    return result
