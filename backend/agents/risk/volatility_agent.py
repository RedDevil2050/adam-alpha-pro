import pandas as pd
from backend.utils.data_provider import fetch_price_series
from backend.utils.cache_utils import redis_client
from backend.agents.risk.utils import tracker

agent_name = "volatility_agent"

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
        # Compute daily returns and volatility
        returns = pd.Series(prices).pct_change().dropna()
        vol = float(returns.std())

        # Normalize & verdict: vol < 0.02 → low risk; >0.05 → high risk
        if vol < 0.02:
            score = 1.0
            verdict = "LOW_VOLATILITY"
        elif vol > 0.05:
            score = 0.0
            verdict = "HIGH_VOLATILITY"
        else:
            score = float((0.05 - vol) / 0.03)
            verdict = "MODERATE_VOLATILITY"

        result = {
            "symbol": symbol,
            "verdict": verdict,
            "confidence": round(score, 4),
            "value": round(vol, 4),
            "details": {"volatility": round(vol, 4)},
            "score": score,
            "agent_name": agent_name
        }

    # Cache & track
    await redis_client.set(cache_key, result, ex=3600)
    tracker.update("risk", agent_name, "implemented")
    return result
