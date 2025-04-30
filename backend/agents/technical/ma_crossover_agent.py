import pandas as pd
from backend.utils.data_provider import fetch_ohlcv_series
from backend.utils.cache_utils import get_redis_client
from backend.agents.technical.utils import tracker

agent_name = "ma_crossover_agent"


async def run(symbol: str, short_window: int = 50, long_window: int = 200) -> dict:
    redis_client = get_redis_client()
    cache_key = f"{agent_name}:{symbol}:{short_window}:{long_window}"
    # 1) Cache check
    cached = await redis_client.get(cache_key)
    if cached:
        return cached

    # 2) Fetch OHLCV data
    df = await fetch_ohlcv_series(symbol, source_preference=["api", "scrape"])
    if df is None or df.empty or len(df) < long_window:
        result = {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {},
            "agent_name": agent_name,
        }
    else:
        close = df["close"]
        # 3) Compute moving averages
        short_ma = close.rolling(window=short_window, min_periods=short_window).mean()
        long_ma = close.rolling(window=long_window, min_periods=long_window).mean()

        last_short = short_ma.iloc[-1]
        last_long = long_ma.iloc[-1]
        prev_short = short_ma.iloc[-2]
        prev_long = long_ma.iloc[-2]

        # 4) Determine crossover
        if prev_short <= prev_long and last_short > last_long:
            score = 1.0
            verdict = "BUY"
        elif prev_short >= prev_long and last_short < last_long:
            score = 0.0
            verdict = "AVOID"
        else:
            score = 0.5
            verdict = "HOLD"

        result = {
            "symbol": symbol,
            "verdict": verdict,
            "confidence": score,
            "value": round(last_short - last_long, 4),
            "details": {
                "short_ma": round(last_short, 4),
                "long_ma": round(last_long, 4),
            },
            "score": score,
            "agent_name": agent_name,
        }

    # 5) Cache result for 1 hour
    await redis_client.set(cache_key, result, ex=3600)
    # 6) Update progress tracker
    tracker.update("technical", agent_name, "implemented")

    return result
