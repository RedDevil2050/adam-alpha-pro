import pandas as pd
import numpy as np
from backend.utils.data_provider import fetch_ohlcv_series
from backend.utils.cache_utils import redis_client
from backend.agents.technical.utils import tracker
from .advanced_indicators import calculate_hurst_exponent, calculate_momentum_quality

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
        volume = df["volume"]
        
        # Advanced indicators
        hurst = calculate_hurst_exponent(close)
        momentum_quality = calculate_momentum_quality(close)
        
        # Enhanced MACD calculation
        ema_short = close.ewm(span=12, adjust=False).mean()
        ema_long = close.ewm(span=26, adjust=False).mean()
        macd_line = ema_short - ema_long
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        
        # Composite scoring with new metrics
        histogram = float(macd_line.iloc[-1] - signal_line.iloc[-1])
        trend_strength = 1 if hurst > 0.5 else 0
        quality_score = momentum_quality / 100
        
        composite_score = (
            0.4 * (1 if histogram > 0 else 0) +
            0.3 * trend_strength +
            0.3 * quality_score
        )
        
        result = {
            "symbol": symbol,
            "verdict": "BUY" if composite_score > 0.5 else "SELL",
            "confidence": round(composite_score * 100, 2),
            "value": round(histogram, 4),
            "details": {
                "histogram": round(histogram, 4),
                "hurst": round(hurst, 4),
                "momentum_quality": round(momentum_quality, 2),
                "composite_score": round(composite_score, 4)
            },
            "score": composite_score,
            "agent_name": agent_name
        }

    # 6) Cache result for 1 hour
    await redis_client.set(cache_key, result, ex=3600)
    # 7) Track progress
    tracker.update("technical", agent_name, "implemented")

    return result
