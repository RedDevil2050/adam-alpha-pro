import pandas as pd
from backend.utils.data_provider import fetch_ohlcv_series
from backend.utils.cache_utils import redis_client
from backend.agents.technical.utils import tracker

agent_name = "adx_agent"


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
            "agent_name": agent_name,
        }
    else:
        high = df["high"]
        low = df["low"]
        close = df["close"]
        prev_close = close.shift(1)

        # 3) True Range and ATR
        tr = pd.concat(
            [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
        ).max(axis=1)
        atr = tr.rolling(window=14, min_periods=14).mean()

        # 4) Directional Movements
        up_move = high - high.shift(1)
        down_move = low.shift(1) - low
        plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
        minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)

        # 5) Directional Indicators
        plus_di = 100 * plus_dm.rolling(window=14, min_periods=14).mean() / atr
        minus_di = 100 * minus_dm.rolling(window=14, min_periods=14).mean() / atr

        # 6) DX and ADX
        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
        adx = dx.rolling(window=14, min_periods=14).mean().iloc[-1]
        adx = float(adx)

        # 7) Normalize & Verdict
        if adx > 25:
            score = 1.0
            verdict = "STRONG_TREND"
        elif adx < 20:
            score = 0.0
            verdict = "NO_TREND"
        else:
            score = (adx - 20) / 5.0
            verdict = "TRENDING"

        result = {
            "symbol": symbol,
            "verdict": verdict,
            "confidence": score,
            "value": adx,
            "details": {"adx": adx},
            "score": score,
            "agent_name": agent_name,
        }

    # 8) Cache result for 1 hour
    await redis_client.set(cache_key, result, ex=3600)
    # 9) Update progress tracker
    tracker.update("technical", agent_name, "implemented")

    return result
