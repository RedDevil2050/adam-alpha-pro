from backend.utils.data_provider import fetch_price_series
import numpy as np
import pandas as pd
from loguru import logger
from backend.agents.decorators import standard_agent_execution  # Import decorator

agent_name = "var_agent"
AGENT_CATEGORY = "risk"  # Define category for the decorator


# Apply the decorator to the standalone run function
@standard_agent_execution(
    agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=3600
)
async def run(
    symbol: str, agent_outputs: dict = None
) -> dict:  # Added agent_outputs default
    # Boilerplate (cache check, try/except, cache set, tracker, error handling) is handled by decorator
    # Core logic moved from the previous _execute method

    prices = await fetch_price_series(symbol)
    # Use a reasonable lookback period, e.g., 252 trading days (1 year)
    min_days = 60  # Keep minimum requirement
    if prices is None or prices.empty or len(prices) < min_days:
        # Return NO_DATA format
        return {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {
                "reason": f"Insufficient price history for VaR calculation (need {min_days}, got {len(prices) if prices else 0})"
            },
            "agent_name": agent_name,
        }

    # Calculate log returns
    # Ensure prices are numeric and handle potential issues
    try:
        numeric_prices = pd.to_numeric(prices, errors="coerce").dropna()
        if len(numeric_prices) < 2:
            raise ValueError("Not enough numeric price points after cleaning.")
        returns = np.diff(np.log(numeric_prices))
    except Exception as e:
        logger.error(f"Error calculating returns for {symbol}: {e}")
        return {
            "symbol": symbol,
            "verdict": "ERROR",
            "confidence": 0.0,
            "value": None,
            "details": {"reason": f"Failed to calculate returns: {str(e)}"},
            "agent_name": agent_name,
        }

    if len(returns) == 0:
        return {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {"reason": "Could not calculate returns from price data"},
            "agent_name": agent_name,
        }

    # Calculate Value at Risk (VaR)
    var_95 = np.percentile(returns, 5)  # 5th percentile for 95% VaR
    var_99 = np.percentile(returns, 1)  # 1st percentile for 99% VaR

    # Annualize VaR (optional, depends on interpretation preference)
    # Scaling by sqrt(252) assumes returns are normally distributed and i.i.d., which might not hold.
    # Reporting daily VaR might be less assumption-prone.
    # var_95_annual = var_95 * np.sqrt(252)
    # var_99_annual = var_99 * np.sqrt(252)

    # Use daily VaR for verdict and value
    daily_var_95 = var_95

    # Normalize to score/confidence based on daily VaR (e.g., higher loss = lower confidence/higher risk)
    # Example: Map -1% VaR to 0.9 confidence, -5% VaR to 0.1 confidence
    # This mapping is subjective and needs tuning.
    # Let's use a simple linear mapping for demonstration:
    # Map VaR range [-0.05, 0] to confidence [0.1, 0.9]
    confidence = 0.9 + (daily_var_95 / 0.05) * 0.8  # Clamp between 0.1 and 0.9
    confidence = min(0.9, max(0.1, confidence))

    # Verdict based on daily VaR 95%
    if daily_var_95 > -0.01:  # Less than 1% potential daily loss
        verdict = "LOW_VAR"
    elif daily_var_95 > -0.03:  # Between 1% and 3% potential daily loss
        verdict = "MODERATE_VAR"
    else:  # More than 3% potential daily loss
        verdict = "HIGH_VAR"

    # Create success result dictionary
    result = {
        "symbol": symbol,
        "verdict": verdict,
        "confidence": round(confidence, 4),
        "value": round(
            -daily_var_95 * 100, 2
        ),  # Report positive percentage loss for 95% VaR
        "details": {
            "daily_var_95_percent": round(-daily_var_95 * 100, 2),
            "daily_var_99_percent": round(-var_99 * 100, 2),
            "calculation_period_days": len(prices),
        },
        "agent_name": agent_name,
    }

    # Decorator handles caching and tracker update
    return result


# The VaRAgent class and RiskAgentBase dependency might be removable
# if this standalone run function is sufficient and RiskAgentBase
# doesn't provide other essential shared functionality used elsewhere.
# Keep the class definition commented out or remove if no longer needed.

# class VaRAgent(RiskAgentBase):
#     async def _execute(self, symbol: str, agent_outputs: dict) -> dict:
#         # ... logic moved to run() ...
#         pass
