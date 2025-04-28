import pandas as pd
import numpy as np
from backend.utils.data_provider import fetch_price_series
from backend.agents.decorators import standard_agent_execution

agent_name = "volatility_agent"
AGENT_CATEGORY = "risk"

@standard_agent_execution(agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=3600)
async def run(symbol: str) -> dict:
    # Fetch price series
    prices = await fetch_price_series(symbol)
    if not prices or len(prices) < 2:
        return {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {"reason": f"Insufficient price data for {symbol}"},
            "agent_name": agent_name
        }

    # Compute daily returns and volatility
    prices_array = np.array(prices)
    returns = np.diff(prices_array) / prices_array[:-1]
    if len(returns) == 0:
        return {
            "symbol": symbol, "verdict": "NO_DATA", "confidence": 0.0, "value": None,
            "details": {"reason": "Could not calculate returns from price data"},
            "agent_name": agent_name
        }

    daily_volatility = np.std(returns)
    annualized_volatility = daily_volatility * np.sqrt(252)

    # Normalize & verdict based on annualized volatility
    if annualized_volatility < 0.20:
        confidence = 0.9
        verdict = "LOW_VOLATILITY"
    elif annualized_volatility < 0.40:
        confidence = 0.7 - (annualized_volatility - 0.20) * (0.4 / 0.20)
        confidence = max(0.3, confidence)
        verdict = "MODERATE_VOLATILITY"
    else:
        confidence = 0.1
        verdict = "HIGH_VOLATILITY"

    # Create the success result dictionary
    result = {
        "symbol": symbol,
        "verdict": verdict,
        "confidence": round(confidence, 4),
        "value": round(annualized_volatility * 100, 2),
        "details": {
            "annualized_volatility_percent": round(annualized_volatility * 100, 2),
            "daily_volatility": round(daily_volatility, 6)
            },
        "agent_name": agent_name
    }

    return result
