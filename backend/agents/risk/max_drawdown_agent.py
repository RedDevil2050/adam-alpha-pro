import pandas as pd
from backend.utils.data_provider import fetch_price_series
from backend.utils.cache_utils import redis_client
from backend.agents.risk.utils import tracker

agent_name = "max_drawdown_agent"

async def run(symbol: str) -> dict:
    cache_key = f"{agent_name}:{symbol}"
    # Cache check
    cached = await redis_client.get(cache_key)
    if cached:
        return cached

    # Fetch price series
    prices = await fetch_price_series(symbol)
    if not prices or len(prices) < 2:
        result = {"symbol": symbol, "verdict": "NO_DATA", "confidence": 0.0, "value": None, "details": {}, "agent_name": agent_name}
    else:
        series = pd.Series(prices)
        # Compute drawdown
        cum_max = series.cummax()
        drawdown = ((series / cum_max) - 1).min()
        dd = float(drawdown)

        # Normalize & verdict: dd > -0.1 → low drawdown; < -0.3 → high drawdown
        if dd > -0.1:
            score = 1.0
            verdict = "LOW_DRAWDOWN"
        elif dd < -0.3:
            score = 0.0
            verdict = "HIGH_DRAWDOWN"
        else:
            score = float((dd + 0.3) / 0.2)
            verdict = "MODERATE_DRAWDOWN"

        result = {
            "symbol": symbol,
            "verdict": verdict,
            "confidence": round(score, 4),
            "value": round(dd, 4),
            "details": {"drawdown": round(dd, 4)},
            "score": score,
            "agent_name": agent_name
        }

    # Cache & track
    await redis_client.set(cache_key, result, ex=3600)
    tracker.update("risk", agent_name, "implemented")
    return result
