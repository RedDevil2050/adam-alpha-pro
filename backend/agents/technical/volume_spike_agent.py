import pandas as pd
from backend.utils.data_provider import fetch_ohlcv_series
from backend.utils.cache_utils import redis_client
from backend.agents.technical.utils import tracker

agent_name = "volume_spike_agent"

async def run(symbol: str, window: int = 20) -> dict:
    cache_key = f"{agent_name}:{symbol}:{window}"
    # 1) Cache check
    cached = await redis_client.get(cache_key)
    if cached:
        return cached

    # 2) Fetch OHLCV data
    df = await fetch_ohlcv_series(symbol, source_preference=["api", "scrape"])
    if df is None or df.empty or len(df) < window:
        result = {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {},
            "agent_name": agent_name
        }
    else:
        volume = df["volume"]
        avg_vol = volume.rolling(window=window, min_periods=window).mean().iloc[-1]
        current_vol = volume.iloc[-1]
        vol_ratio = current_vol / avg_vol if avg_vol > 0 else 0

        # 3) Normalize and verdict
        if vol_ratio >= 2:
            score = 1.0
            verdict = "HIGH_SPIKE"
        elif vol_ratio <= 1:
            score = 0.0
            verdict = "NORMAL"
        else:
            score = (vol_ratio - 1) / 1.0
            verdict = "MODERATE_SPIKE"

        result = {
            "symbol": symbol,
            "verdict": verdict,
            "confidence": score,
            "value": round(vol_ratio, 4),
            "details": {
                "avg_vol": round(avg_vol, 2),
                "current_vol": int(current_vol)
            },
            "score": score,
            "agent_name": agent_name
        }

    # 4) Cache result for 1 hour
    await redis_client.set(cache_key, result, ex=3600)
    # 5) Update progress tracker
    tracker.update("technical", agent_name, "implemented")

    return result
