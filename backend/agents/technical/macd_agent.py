import pandas as pd
from backend.utils.data_provider import fetch_ohlcv_series
from backend.utils.cache_utils import redis_client
from backend.agents.technical.utils import tracker

agent_name = "macd_agent"

async def run(symbol: str) -> dict:
    cache_key = f"{agent_name}:{symbol}"
    # 1) Cache check
    cached = await redis_client.get(cache_key)
    if cached:
        return cached

    # 2) Fetch OHLCV (API first, then scraper)
    df = await fetch_ohlcv_series(symbol, source_preference=["api", "scrape"])
    if df is None or df.empty:
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
        # 3) Compute MACD line and signal line
        ema_short = close.ewm(span=12, adjust=False).mean()
        ema_long = close.ewm(span=26, adjust=False).mean()
        macd_line = ema_short - ema_long
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        # 4) Histogram
        hist_series = macd_line - signal_line
        histogram = float(hist_series.iloc[-1])
        max_hist = float(hist_series.max()) if hist_series.max() != 0 else abs(histogram)
        min_hist = float(hist_series.min()) if hist_series.min() != 0 else abs(histogram)
        # 5) Normalize to [0,1]
        if histogram > 0:
            score = min(histogram / max_hist, 1.0)
            verdict = "BUY"
        elif histogram < 0:
            score = min(histogram / abs(min_hist), 1.0)
            verdict = "AVOID"
        else:
            score = 0.0
            verdict = "HOLD"

        result = {
            "symbol": symbol,
            "verdict": verdict,
            "confidence": score,
            "value": round(histogram, 4),
            "details": {"histogram": round(histogram, 4)},
            "score": score,
            "agent_name": agent_name
        }

    # 6) Cache result for 1 hour
    await redis_client.set(cache_key, result, ex=3600)
    # 7) Track progress
    tracker.update("technical", agent_name, "implemented")

    return result
