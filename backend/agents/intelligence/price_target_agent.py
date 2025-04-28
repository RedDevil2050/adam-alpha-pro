"""Auto-refactored price_target_agent agent."""

import numpy as np
from backend.utils.cache_utils import redis_client
from backend.utils.data_provider import fetch_price_series
from backend.agents.intelligence.utils import tracker

agent_name = "price_target_agent"

async def run(symbol: str, agent_outputs: dict = {}) -> dict:
    cache_key = f"{agent_name}:{symbol}"
    cached = await redis_client.get(cache_key)
    if cached:
        return cached

    try:
        # Fetch price series (60 days)
        prices = await fetch_price_series(symbol, source_preference=["api", "scrape"])
        if not prices or len(prices) < 2:
            result = {
                "symbol": symbol,
                "verdict": "NO_DATA",
                "confidence": 0.0,
                "value": None,
                "details": {},
                "agent_name": agent_name
            }
        else:
            # Calculate price target using linear regression
            x = np.arange(len(prices))
            slope, intercept = np.polyfit(x, prices, 1)
            price_target = slope * (len(prices) + 30) + intercept  # 30 days into the future

            # Normalize confidence based on slope
            confidence = min(abs(slope) / np.mean(prices), 1.0) if np.mean(prices) != 0 else 0.0
            verdict = "UPTREND" if slope > 0 else "DOWNTREND"

            result = {
                "symbol": symbol,
                "verdict": verdict,
                "confidence": round(confidence, 4),
                "value": round(price_target, 2),
                "details": {"slope": round(slope, 4), "intercept": round(intercept, 4)},
                "agent_name": agent_name
            }

        await redis_client.set(cache_key, result, ex=3600)
        tracker.update("intelligence", agent_name, "implemented")
        return result

    except Exception as e:
        return {
            "symbol": symbol,
            "verdict": "ERROR",
            "confidence": 0.0,
            "value": None,
            "details": {},
            "error": str(e),
            "agent_name": agent_name
        }
