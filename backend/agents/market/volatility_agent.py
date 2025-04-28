from backend.utils.data_provider import fetch_price_series
import numpy as np
from loguru import logger
from backend.agents.decorators import standard_agent_execution # Import decorator

agent_name = "volatility_agent"
AGENT_CATEGORY = "market" # Define category for the decorator

# Apply the decorator to the standalone run function
@standard_agent_execution(agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=3600)
async def run(symbol: str, agent_outputs: dict = None) -> dict: # Added agent_outputs default
    # Boilerplate (cache check, try/except, cache set, tracker, error handling) is handled by decorator
    # Core logic moved from the previous _execute method

    prices = await fetch_price_series(symbol)
    min_days_30d = 30
    min_days_90d = 90
    min_days_hist = 252 # For historical percentile calculation
    required_days = max(min_days_30d, min_days_90d, min_days_hist)

    if not prices or len(prices) < min_days_30d: # Need at least 30 days for basic calculation
        # Return NO_DATA format
        return {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {"reason": f"Insufficient price history for {symbol} (need {min_days_30d} days)"},
            "agent_name": agent_name
        }

    # Calculate rolling volatility metrics (Core Logic)
    prices_arr = np.array(prices)
    log_returns = np.diff(np.log(prices_arr))

    if len(log_returns) < min_days_30d - 1:
        return {
            "symbol": symbol, "verdict": "NO_DATA", "confidence": 0.0, "value": None,
            "details": {"reason": f"Insufficient returns data ({len(log_returns)} points) for 30d volatility"},
            "agent_name": agent_name
        }

    # Calculate annualized volatilities
    vol_30d = np.std(log_returns[-(min_days_30d-1):]) * np.sqrt(252)

    if len(log_returns) >= min_days_90d - 1:
        vol_90d = np.std(log_returns[-(min_days_90d-1):]) * np.sqrt(252)
    else:
        vol_90d = np.nan # Not enough data for 90d vol

    # Calculate historical percentile of *returns* (original code was ambiguous)
    # If the goal is percentile of volatility, that requires calculating rolling volatility first.
    # Assuming percentile of returns as in original code:
    # Use a longer history if available for percentile calculation
    hist_returns_period = min(len(log_returns), min_days_hist - 1)
    return_percentile_90 = np.percentile(log_returns[-hist_returns_period:], 90) if hist_returns_period > 0 else np.nan

    # Historical volatility over the available period (up to ~1 year)
    hist_vol = np.std(log_returns[-hist_returns_period:]) * np.sqrt(252) if hist_returns_period > 0 else np.nan

    # Determine regime based on 30d vs 90d volatility (Core Logic)
    # Handle case where 90d vol is NaN
    if np.isnan(vol_90d):
        # Cannot compare 30d vs 90d, use a simpler verdict based on 30d level
        if vol_30d > 0.4: # Example threshold for high vol
             verdict = "HIGH_VOLATILITY"
             confidence = 0.7
        elif vol_30d < 0.15: # Example threshold for low vol
             verdict = "LOW_VOLATILITY"
             confidence = 0.7
        else:
             verdict = "NORMAL_VOLATILITY"
             confidence = 0.5
    elif vol_30d > vol_90d * 1.5:
        verdict = "HIGH_VOLATILITY_EXPANDING" # More descriptive verdict
        confidence = 0.8 # Adjusted confidence
    elif vol_30d < vol_90d * 0.7: # Adjusted threshold
        verdict = "LOW_VOLATILITY_CONTRACTING" # More descriptive verdict
        confidence = 0.7 # Adjusted confidence
    else:
        verdict = "NORMAL_VOLATILITY"
        confidence = 0.6

    # Create success result dictionary (Core Logic)
    result = {
        "symbol": symbol,
        "verdict": verdict,
        "confidence": round(confidence, 4),
        "value": round(vol_30d * 100, 2), # Report 30d annualized volatility percentage
        "details": {
            "annualized_vol_30d_percent": round(vol_30d * 100, 2),
            "annualized_vol_90d_percent": round(vol_90d * 100, 2) if not np.isnan(vol_90d) else None,
            "historical_annualized_vol_percent": round(hist_vol * 100, 2) if not np.isnan(hist_vol) else None,
            "return_90th_percentile_daily": round(return_percentile_90, 6) if not np.isnan(return_percentile_90) else None,
            "calculation_period_days": len(prices)
        },
        "agent_name": agent_name
    }

    # Decorator handles caching and tracker update
    return result
