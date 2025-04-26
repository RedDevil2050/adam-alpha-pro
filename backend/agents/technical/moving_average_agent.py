import pandas as pd
from backend.utils.data_provider import fetch_ohlcv_series
from backend.utils.cache_utils import redis_client
from backend.agents.technical.utils import tracker

agent_name = "moving_average_agent"

async def run(symbol: str, window: int = 20) -> dict:
    cache_key = f"{agent_name}:{symbol}:{window}"
    # 1) Cache check
    cached = await redis_client.get(cache_key)
    if cached:
        return cached

    # 2) Fetch OHLCV data (API first, then scraper)
    df = await fetch_ohlcv_series(symbol, source_preference=["api", "scrape"])
    if df is None or df.empty or len(df) < window + 1:
        result = {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {},
            "agent_name": agent_name
        }
    else:
        close = df["close"]
        ma = close.rolling(window=window, min_periods=window).mean()
        # Calculate slope percentage of MA
        ma_last = ma.iloc[-1]
        ma_prev = ma.iloc[-2]
        slope_pct = (ma_last - ma_prev) / ma_prev if ma_prev != 0 else 0.0

        # Normalize and verdict
        if slope_pct > 0:
            score = min(slope_pct * 10, 1.0)
            verdict = "BUY"
        elif slope_pct < 0:
            score = 0.0
            verdict = "AVOID"
        else:
            score = 0.5
            verdict = "HOLD"

        result = {
            "symbol": symbol,
            "verdict": verdict,
            "confidence": score,
            "value": round(slope_pct, 4),
            "details": {
                "ma_last": round(ma_last, 4),
                "ma_prev": round(ma_prev, 4),
                "slope_pct": round(slope_pct, 4)
            },
            "score": score,
            "agent_name": agent_name
        }

    # 3) Cache result for 1 hour
    await redis_client.set(cache_key, result, ex=3600)
    # 4) Update progress tracker
    tracker.update("technical", agent_name, "implemented")

    return result
