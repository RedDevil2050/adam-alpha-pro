import pandas as pd
from backend.utils.data_provider import fetch_ohlcv_series
from backend.utils.cache_utils import get_redis_client
from backend.agents.technical.utils import tracker
from datetime import datetime, timedelta

agent_name = "moving_average_agent"


async def run(symbol: str, window: int = 20, agent_outputs: dict = None) -> dict:
    cache_key = f"{agent_name}:{symbol}:{window}"
    redis_client = get_redis_client()
    # 1) Cache check
    cached = await redis_client.get(cache_key)
    if cached:
        return cached

    # Define date range for the past year
    end_date = datetime(2025, 4, 30)
    start_date = end_date - timedelta(days=365)
    end_date_str = end_date.strftime('%Y-%m-%d')
    start_date_str = start_date.strftime('%Y-%m-%d')

    # 2) Fetch OHLCV data
    df = await fetch_ohlcv_series(symbol, start_date=start_date_str, end_date=end_date_str)
    if df is None or df.empty or len(df) < window + 1:
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
                "slope_pct": round(slope_pct, 4),
            },
            "score": score,
            "agent_name": agent_name,
        }

    # 3) Cache result for 1 hour
    await redis_client.set(cache_key, result, ex=3600)
    # 4) Update progress tracker
    tracker.update("technical", agent_name, "implemented")

    return result
