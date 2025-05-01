import pandas as pd
from backend.utils.data_provider import fetch_ohlcv_series
from backend.utils.cache_utils import get_redis_client
from backend.agents.technical.utils import tracker

agent_name = "stochastic_oscillator_agent"


async def run(symbol: str) -> dict:
    cache_key = f"{agent_name}:{symbol}"
    redis_client = await get_redis_client()
    # Cache check
    cached = await redis_client.get(cache_key)
    if cached:
        return cached

    # Fetch data
    df = await fetch_ohlcv_series(symbol, source_preference=["api", "scrape"])
    if df is None or df.empty:
        result = {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {},
            "agent_name": agent_name,
        }
    else:
        # Compute fast %K and %D
        low_min = df["low"].rolling(14).min()
        high_max = df["high"].rolling(14).max()
        k = 100 * ((df["close"] - low_min) / (high_max - low_min))
        d = k.rolling(3).mean()
        latest_k, latest_d = float(k.iloc[-1]), float(d.iloc[-1])
        prev_k, prev_d = float(k.iloc[-2]), float(d.iloc[-2])

        # Crossover logic
        if prev_k <= prev_d and latest_k > latest_d:
            verdict = "BUY"
            score = 1.0
        elif prev_k >= prev_d and latest_k < latest_d:
            verdict = "AVOID"
            score = 0.0
        else:
            verdict = "HOLD"
            score = 0.5

        result = {
            "symbol": symbol,
            "verdict": verdict,
            "confidence": score,
            "value": round(latest_k - latest_d, 4),
            "details": {"k": latest_k, "d": latest_d},
            "score": score,
            "agent_name": agent_name,
        }

    # Cache and track
    await redis_client.set(cache_key, result, ex=3600)
    tracker.update("technical", agent_name, "implemented")
    return result
