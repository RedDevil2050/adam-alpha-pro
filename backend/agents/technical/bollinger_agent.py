import pandas as pd
from backend.utils.data_provider import fetch_ohlcv_series
from backend.utils.cache_utils import redis_client
from backend.agents.technical.utils import tracker

agent_name = "bollinger_agent"

async def run(symbol: str, window: int = 20, num_std: float = 2.0) -> dict:
    cache_key = f"{agent_name}:{symbol}:{window}:{num_std}"
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
        close = df["close"]
        # 3) Compute moving average and standard deviation
        ma = close.rolling(window=window, min_periods=window).mean()
        std = close.rolling(window=window, min_periods=window).std()

        last_ma = ma.iloc[-1]
        last_std = std.iloc[-1]
        last_close = close.iloc[-1]

        upper_band = last_ma + num_std * last_std
        lower_band = last_ma - num_std * last_std

        # 4) Normalize and map verdict
        if last_close < lower_band:
            score = 1.0
            verdict = "BUY"
        elif last_close > upper_band:
            score = 0.0
            verdict = "AVOID"
        else:
            # Position between bands: invert relative position
            score = float((upper_band - last_close) / (upper_band - lower_band))
            verdict = "HOLD"

        result = {
            "symbol": symbol,
            "verdict": verdict,
            "confidence": score,
            "value": round(last_close, 4),
            "details": {
                "upper_band": round(upper_band, 4),
                "lower_band": round(lower_band, 4),
                "moving_average": round(last_ma, 4),
                "std_dev": round(last_std, 4)
            },
            "score": score,
            "agent_name": agent_name
        }

    # 5) Cache result for 1 hour
    await redis_client.set(cache_key, result, ex=3600)
    # 6) Update progress tracker
    tracker.update("technical", agent_name, "implemented")

    return result
