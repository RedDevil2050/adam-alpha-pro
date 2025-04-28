import numpy as np
from backend.utils.data_provider import fetch_price_series
from backend.utils.cache_utils import redis_client
from backend.agents.risk.utils import tracker

agent_name = "drawdown_agent"

async def run(symbol: str) -> dict:
    cache_key = f"{agent_name}:{symbol}"
    cached = await redis_client.get(cache_key)
    if cached:
        return cached

    try:
        # Fetch price series
        prices = await fetch_price_series(symbol)
        if not prices or len(prices) < 2:
            return {
                "symbol": symbol,
                "verdict": "NO_DATA",
                "confidence": 0.0,
                "value": None,
                "details": {},
                "agent_name": agent_name
            }

        # Calculate drawdown
        prices = np.array(prices)
        peak = np.maximum.accumulate(prices)
        drawdowns = (prices - peak) / peak
        max_drawdown = drawdowns.min()

        # Verdict based on drawdown
        if max_drawdown > -0.1:
            verdict = "LOW_DRAWDOWN"
            confidence = 0.9
        elif max_drawdown > -0.2:
            verdict = "MODERATE_DRAWDOWN"
            confidence = 0.7
        else:
            verdict = "HIGH_DRAWDOWN"
            confidence = 0.5

        result = {
            "symbol": symbol,
            "verdict": verdict,
            "confidence": round(confidence, 4),
            "value": round(max_drawdown * 100, 2),
            "details": {"max_drawdown": round(max_drawdown * 100, 2)},
            "agent_name": agent_name
        }

        await redis_client.set(cache_key, result, ex=3600)
        tracker.update("risk", agent_name, "implemented")
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