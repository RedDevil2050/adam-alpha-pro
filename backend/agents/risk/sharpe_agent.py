import numpy as np
from backend.utils.data_provider import fetch_price_series
from backend.agents.decorators import standard_agent_execution # Import decorator

agent_name = "sharpe_agent"
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
        }

    # Calculate daily returns (Core Logic)
    returns = np.diff(np.log(prices))

    # Risk-free rate (annualized)
    risk_free_rate = 0.04  # Example: 4%
    daily_risk_free_rate = risk_free_rate / 252

    # Calculate Sharpe ratio (Core Logic)
    excess_returns = returns - daily_risk_free_rate
    # Handle potential division by zero if std dev is zero
    std_dev = np.std(excess_returns)
    if std_dev == 0:
        sharpe_ratio = 0.0 # Or handle as appropriate (e.g., return specific verdict)
    else:
        sharpe_ratio = np.sqrt(252) * np.mean(excess_returns) / std_dev


    # Verdict based on Sharpe ratio (Core Logic)
    if sharpe_ratio > 2:
        verdict = "EXCELLENT"
        confidence = 0.9
    elif sharpe_ratio > 1:
        verdict = "GOOD"
        confidence = 0.7
    else:
        verdict = "POOR"
        confidence = 0.5

    # Create the success result dictionary (Core Logic)
    # Decorator handles caching this result and adding agent_name if missing
    result = {
        "symbol": symbol,
        "verdict": verdict,
        "confidence": round(confidence, 4),
        "value": round(sharpe_ratio, 4),
        "details": {"sharpe_ratio": round(sharpe_ratio, 4)},
    }
    return result
    # Error handling is done by the decorator's except block
    # Cache setting is done by the decorator
    # Tracker update is handled (conceptually) by the decorator