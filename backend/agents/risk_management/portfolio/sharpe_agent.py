import numpy as np
import pandas as pd # Import pandas
from backend.utils.data_provider import fetch_price_series
from backend.agents.decorators import standard_agent_execution  # Import decorator

agent_name = "sharpe_agent"
AGENT_CATEGORY = "risk"  # Define category for the decorator

# Define constants matching the test file
ANNUAL_RISK_FREE_RATE = 0.02
ANNUALIZATION_FACTOR = 252

# Define verdict thresholds matching the test file
SHARPE_THRESHOLDS = {
    "GOOD_RISK_ADJUSTED_RETURN": 1.0,
    "AVERAGE_RISK_ADJUSTED_RETURN": 0.5,
    "POOR_RISK_ADJUSTED_RETURN": 0.0
}


# Apply the decorator
@standard_agent_execution(
    agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=3600
)
async def run(symbol: str) -> dict:
    # Boilerplate (cache check, try/except, cache set, tracker, error handling) is handled by decorator

    # Fetch price series (Core Logic)
    prices = await fetch_price_series(symbol)
    # Corrected check for empty/None pandas Series and sufficient length
    if prices is None or not isinstance(prices, pd.Series) or prices.empty or len(prices) < 2:
        # Return the standard NO_DATA format (decorator won't cache this)
        # Decorator will add agent_name if missing
        return {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {"message": "Insufficient price data available."},
        }

    # Calculate daily returns using percentage change (Core Logic)
    returns = prices.pct_change().dropna()

    # Check if enough returns exist after dropping NaN
    if returns.empty or len(returns) < 1: # Need at least one return to calculate mean/std
         return {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {"message": "Could not calculate returns from price data."},
        }


    # Calculate daily risk-free rate from annual rate
    # Using approximation consistent with test: annual_rf / annualization_factor
    daily_risk_free_rate = ANNUAL_RISK_FREE_RATE / ANNUALIZATION_FACTOR

    # Calculate average daily return and standard deviation of daily return
    mean_daily_return = returns.mean()
    std_daily_return = returns.std()


    # Handle case of zero volatility (Core Logic)
    if std_daily_return == 0:
        # If std dev is 0, Sharpe is undefined or infinite.
        # Assign a large positive value if mean return > risk-free, else 0 or negative.
        # For simplicity matching test assumptions (which avoid this), return 0 for now.
        # A more robust implementation might return np.inf or a specific verdict.
        sharpe_ratio = 0.0 # Consistent with previous agent logic, though test handles differently
    else:
        # Calculate daily excess return
        excess_return = mean_daily_return - daily_risk_free_rate
        # Calculate daily Sharpe Ratio
        daily_sharpe = excess_return / std_daily_return
        # Annualize the Sharpe Ratio
        sharpe_ratio = daily_sharpe * np.sqrt(ANNUALIZATION_FACTOR)


    # Determine verdict based on Sharpe ratio and thresholds (Core Logic)
    # Sort thresholds by value descending to apply the highest threshold first
    sorted_thresholds = sorted(SHARPE_THRESHOLDS.items(), key=lambda item: item[1], reverse=True)

    verdict = "POOR_RISK_ADJUSTED_RETURN" # Default if below all thresholds
    confidence = 0.5 # Default confidence

    for v, threshold_value in sorted_thresholds:
        if sharpe_ratio >= threshold_value:
            verdict = v
            # Assign confidence based on verdict (example logic, can be refined)
            if v == "GOOD_RISK_ADJUSTED_RETURN":
                confidence = 0.9
            elif v == "AVERAGE_RISK_ADJUSTED_RETURN":
                confidence = 0.7
            # Keep default 0.5 for POOR
            break # Stop at the first matching threshold


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
