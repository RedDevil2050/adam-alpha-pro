import pandas as pd
import numpy as np
from backend.utils.cache_utils import redis_client
from backend.utils.data_provider import fetch_price_series
from backend.agents.forecast.utils import tracker

agent_name = "price_forecast_agent"

async def run(symbol: str) -> dict:
    cache_key = f"{agent_name}:{symbol}"
    cached = await redis_client.get(cache_key)
    if cached:
        return cached

    # Fetch price series (60 days)
    prices = await fetch_price_series(symbol, source_preference=["api","scrape"])
    if not prices or len(prices) < 2:
        result = {"symbol": symbol, "verdict": "NO_DATA", "confidence": 0.0, "value": None,
                  "details": {}, "score": 0.0, "agent_name": agent_name}
    else:
        series = pd.Series(prices)
        # Fit linear trend
        x = np.arange(len(series))
        slope = float(np.polyfit(x, series, 1)[0])
        if slope > 0:
            verdict = "UPTREND"
            # Normalize via average price
            score = min(slope / series.mean(), 1.0) if series.mean() != 0 else 1.0
        else:
            verdict = "DOWNTREND"
            score = min(abs(slope) / series.mean(), 1.0) if series.mean() != 0 else 1.0

        result = {
            "symbol": symbol,
            "verdict": verdict,
            "confidence": round(score, 4),
            "value": slope,
            "details": {"slope": slope},
            "score": score,
            "agent_name": agent_name
        }

    await redis_client.set(cache_key, result, ex=None)
    tracker.update("forecast", agent_name, "implemented")
    return result
