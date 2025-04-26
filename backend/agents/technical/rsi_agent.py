import pandas as pd
from backend.utils.data_provider import fetch_ohlcv_series
from backend.utils.cache_utils import redis_client
from backend.agents.technical.utils import compute_rsi, normalize_rsi, tracker

agent_name = "rsi_agent"

async def run(symbol: str) -> dict:
    cache_key = f"{agent_name}:{symbol}"
    # 1) Cache check
    cached = await redis_client.get(cache_key)
    if cached:
        return cached

    # 2) Fetch OHLCV (API first, then scraper)
    df = await fetch_ohlcv_series(symbol, source_preference=["api", "scrape"])
    if df is None or df.empty:
        result = {"symbol": symbol, "verdict": "NO_DATA", "confidence": 0.0, "value": None, "details": {}, "agent_name": agent_name}
    else:
        # 3) Compute RSI and normalize score
        rsi = compute_rsi(df["close"])
        score = normalize_rsi(rsi)
        result = {
            "symbol": symbol,
            "verdict": "BUY" if score == 1.0 else ("AVOID" if score == 0.0 else "HOLD"),
            "confidence": 1.0,
            "value": round(rsi, 2),
            "details": {"rsi": round(rsi, 2)},
            "score": score,
            "agent_name": agent_name
        }

    # 4) Cache result for 1 hour
    await redis_client.set(cache_key, result, ex=3600)

    # 5) Update progress tracker
    tracker.update("technical", agent_name, "implemented")

    return result
