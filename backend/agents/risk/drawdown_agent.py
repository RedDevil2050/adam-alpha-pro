import numpy as np
from backend.utils.data_provider import fetch_price_series
from backend.agents.decorators import standard_agent_execution # Import decorator

agent_name = "drawdown_agent"
AGENT_CATEGORY = "risk" # Define category for the decorator

# Apply the decorator
@standard_agent_execution(agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=3600)
async def run(symbol: str) -> dict:
    # Boilerplate (cache check, try/except, cache set, tracker, error handling) is handled by decorator

    # Fetch price series (Core Logic)
    prices = await fetch_price_series(symbol)
    if not prices or len(prices) < 2:
        # Return the standard NO_DATA format (decorator won't cache this)
        # Decorator will add agent_name if missing
        return {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {},
            # agent_name will be added by decorator
        }

    # Calculate drawdown (Core Logic)
    prices = np.array(prices)
    peak = np.maximum.accumulate(prices)
    drawdowns = (prices - peak) / peak
    max_drawdown = drawdowns.min()

    # Verdict based on drawdown (Core Logic)
    if max_drawdown > -0.1:
        verdict = "LOW_DRAWDOWN"
        confidence = 0.9
    elif max_drawdown > -0.2:
        verdict = "MODERATE_DRAWDOWN"
        confidence = 0.7
    else:
        verdict = "HIGH_DRAWDOWN"
        confidence = 0.5

    # Create the success result dictionary (Core Logic)
    # Decorator handles caching this result and adding agent_name if missing
    result = {
        "symbol": symbol,
        "verdict": verdict,
        "confidence": round(confidence, 4),
        "value": round(max_drawdown * 100, 2),
        "details": {"max_drawdown": round(max_drawdown * 100, 2)},
        # agent_name will be added by decorator
    }
    return result
    # Error handling is done by the decorator's except block
    # Cache setting is done by the decorator
    # Tracker update is handled (conceptually) by the decorator