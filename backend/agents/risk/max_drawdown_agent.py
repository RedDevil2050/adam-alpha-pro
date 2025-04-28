import pandas as pd
import numpy as np # Import numpy
from backend.utils.data_provider import fetch_price_series
from backend.agents.decorators import standard_agent_execution # Import decorator

agent_name = "max_drawdown_agent"
AGENT_CATEGORY = "risk" # Define category for the decorator

@standard_agent_execution(agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=3600)
async def run(symbol: str) -> dict:
    # Boilerplate (cache check, try/except, cache set, tracker, error handling) is handled by decorator

    # Fetch price series (Core Logic)
    prices = await fetch_price_series(symbol)
    if not prices or len(prices) < 2:
        # Return NO_DATA format (decorator won't cache this)
        return {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {"reason": f"Insufficient price data for {symbol}"},
            "agent_name": agent_name
        }

    # Calculate max drawdown (Core Logic)
    prices_array = np.array(prices)
    peak = np.maximum.accumulate(prices_array)
    # Calculate drawdown, handle potential division by zero if peak is zero
    drawdowns = np.divide(prices_array - peak, peak, out=np.zeros_like(prices_array, dtype=float), where=peak!=0)
    max_drawdown = drawdowns.min()

    # Verdict based on drawdown (Core Logic)
    if max_drawdown > -0.1:
        verdict = "LOW_DRAWDOWN"
        confidence = 0.9
    elif max_drawdown > -0.3: # Adjusted threshold based on original logic
        verdict = "MODERATE_DRAWDOWN"
        confidence = 0.6 # Adjusted confidence based on original logic scale
    else:
        verdict = "HIGH_DRAWDOWN"
        confidence = 0.3 # Adjusted confidence

    # Create the success result dictionary (Core Logic)
    result = {
        "symbol": symbol,
        "verdict": verdict,
        "confidence": round(confidence, 4),
        "value": round(max_drawdown * 100, 2), # Value as percentage
        "details": {"max_drawdown_percentage": round(max_drawdown * 100, 2)},
        # "score": score, # Removed score as confidence serves similar purpose
        "agent_name": agent_name
    }

    # Decorator handles caching and tracker update
    return result
