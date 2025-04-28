import numpy as np
from backend.utils.data_provider import fetch_price_series
from backend.utils.cache_utils import redis_client
from backend.agents.risk.utils import tracker

agent_name = "sharpe_agent"

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

        # Calculate daily returns
        returns = np.diff(np.log(prices))

        # Risk-free rate (annualized)
        risk_free_rate = 0.04  # Example: 4%
        daily_risk_free_rate = risk_free_rate / 252

        # Calculate Sharpe ratio
        excess_returns = returns - daily_risk_free_rate
        sharpe_ratio = np.sqrt(252) * np.mean(excess_returns) / np.std(excess_returns)

        # Verdict based on Sharpe ratio
        if sharpe_ratio > 2:
            verdict = "EXCELLENT"
            confidence = 0.9
        elif sharpe_ratio > 1:
            verdict = "GOOD"
            confidence = 0.7
        else:
            verdict = "POOR"
            confidence = 0.5

        result = {
            "symbol": symbol,
            "verdict": verdict,
            "confidence": round(confidence, 4),
            "value": round(sharpe_ratio, 4),
            "details": {"sharpe_ratio": round(sharpe_ratio, 4)},
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