import pandas as pd
from backend.utils.data_provider import fetch_ohlcv_series
from backend.utils.cache_utils import redis_client
from backend.agents.technical.utils import tracker

agent_name = "trend_strength_agent"

async def run(symbol: str) -> dict:
    cache_key = f"{agent_name}:{symbol}"
    # Cache check
    cached = await redis_client.get(cache_key)
    if cached:
        return cached

    # Fetch data
    df = await fetch_ohlcv_series(symbol, source_preference=["api", "scrape"])
    if df is None or df.empty:
        result = {"symbol": symbol, "verdict": "NO_DATA", "confidence": 0.0, "value": None, "details": {}, "agent_name": agent_name}
    else:
        close = df["close"]
        returns = close.pct_change().dropna()
        ts = abs(returns.rolling(5).mean() / returns.rolling(5).std()).iloc[-1]
        ts = float(ts)
        # Verdict & score
        if ts > 2:
            verdict = "STRONG"
            score = 1.0
        elif ts > 1:
            verdict = "MILD"
            score = (ts - 1) / 1.0
        else:
            verdict = "WEAK"
            score = 0.0

        result = {
            "symbol": symbol,
            "verdict": verdict,
            "confidence": score,
            "value": ts,
            "details": {"trend_strength": ts},
            "score": score,
            "agent_name": agent_name
        }

    # Cache and track
    await redis_client.set(cache_key, result, ex=3600)
    tracker.update("technical", agent_name, "implemented")
    return result
