import pandas as pd
from backend.utils.data_provider import fetch_ohlcv_series
from backend.utils.cache_utils import get_redis_client
from backend.agents.technical.utils import tracker
from backend.config.settings import settings

agent_name = "stochastic_agent"


async def run(symbol: str, agent_outputs: dict = None) -> dict:
    cache_key = f"{agent_name}:{symbol}"
    redis_client = await get_redis_client()
    # Cache check
    cached = await redis_client.get(cache_key)
    if cached:
        return cached

    # Fetch OHLCV series with fallback
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
        low_min = df["low"].rolling(settings.STOCHASTIC_K_WINDOW).min()
        high_max = df["high"].rolling(settings.STOCHASTIC_K_WINDOW).max()
        k = 100 * ((df["close"] - low_min) / (high_max - low_min))
        d = k.rolling(settings.STOCHASTIC_D_WINDOW).mean()
        latest_k = float(k.iloc[-1])
        latest_d = float(d.iloc[-1])

        # Verdict mapping
        if latest_k <= settings.STOCHASTIC_OVERSOLD:
            verdict = "BUY"
            score = 1.0
        elif latest_k >= settings.STOCHASTIC_OVERBOUGHT:
            verdict = "AVOID"
            score = 0.0
        else:
            verdict = "HOLD"
            # linear score: buffer between oversold/overbought
            range_span = settings.STOCHASTIC_OVERBOUGHT - settings.STOCHASTIC_OVERSOLD
            score = max(
                0.0, min(1.0, (settings.STOCHASTIC_OVERBOUGHT - latest_k) / range_span)
            )

        confidence = round(score, 4)
        result = {
            "symbol": symbol,
            "verdict": verdict,
            "confidence": confidence,
            "value": latest_k,
            "details": {"k": latest_k, "d": latest_d},
            "score": score,
            "agent_name": agent_name,
        }

    # Cache and track
    await redis_client.set(cache_key, result, ex=3600)
    tracker.update("technical", agent_name, "implemented")
    return result
