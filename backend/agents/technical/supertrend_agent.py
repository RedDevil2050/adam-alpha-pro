import pandas as pd
from backend.utils.data_provider import fetch_ohlcv_series
from backend.utils.cache_utils import redis_client
from backend.agents.technical.utils import tracker

agent_name = "supertrend_agent"

async def run(symbol: str, multiplier: int = 3, period: int = 10) -> dict:
    cache_key = f"{agent_name}:{symbol}:{period}:{multiplier}"
    # 1) Cache check
    cached = await redis_client.get(cache_key)
    if cached:
        return cached

    # 2) Fetch OHLCV data
    df = await fetch_ohlcv_series(symbol, source_preference=["api", "scrape"])
    if df is None or df.empty or len(df) < period:
        result = {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {},
            "agent_name": agent_name
        }
    else:
        high = df["high"]
        low = df["low"]
        close = df["close"]

        # 3) ATR calculation
        prev_close = close.shift(1)
        tr = pd.concat([
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs()
        ], axis=1).max(axis=1)
        atr = tr.rolling(window=period, min_periods=period).mean()

        # 4) Basic bands
        hl2 = (high + low) / 2
        basic_ub = hl2 + multiplier * atr
        basic_lb = hl2 - multiplier * atr

        # 5) Final bands initialization
        final_ub = basic_ub.copy()
        final_lb = basic_lb.copy()

        for i in range(period, len(df)):
            if (basic_ub[i] < final_ub[i-1]) or (close[i-1] > final_ub[i-1]):
                final_ub.iloc[i] = basic_ub.iloc[i]
            else:
                final_ub.iloc[i] = final_ub.iloc[i-1]
            if (basic_lb[i] > final_lb[i-1]) or (close[i-1] < final_lb[i-1]):
                final_lb.iloc[i] = basic_lb.iloc[i]
            else:
                final_lb.iloc[i] = final_lb.iloc[i-1]

        # 6) Determine Supertrend value and verdict
        # Use the last available point
        last_close = close.iloc[-1]
        last_ub = final_ub.iloc[-1]
        last_lb = final_lb.iloc[-1]

        if last_close > last_ub:
            score = 1.0
            verdict = "BUY"
        elif last_close < last_lb:
            score = 0.0
            verdict = "AVOID"
        else:
            score = 0.5
            verdict = "HOLD"

        result = {
            "symbol": symbol,
            "verdict": verdict,
            "confidence": score,
            "value": round(last_close, 2),
            "details": {
                "supertrend": round(last_ub if last_close > last_ub else last_lb, 2),
                "atr": round(atr.iloc[-1], 4)
            },
            "score": score,
            "agent_name": agent_name
        }

    # 7) Cache result
    await redis_client.set(cache_key, result, ex=3600)
    # 8) Track progress
    tracker.update("technical", agent_name, "implemented")

    return result
