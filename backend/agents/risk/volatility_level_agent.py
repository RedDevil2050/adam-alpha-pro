import pandas as pd
import numpy as np
from backend.utils.data_provider import fetch_price_series
from backend.agents.decorators import standard_agent_execution

agent_name = "volatility_level_agent"
AGENT_CATEGORY = "risk"


@standard_agent_execution(
    agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=3600
)
async def run(symbol: str) -> dict:
    """
    Calculates the annualized volatility level for a given stock symbol.

    Purpose:
        Assesses the absolute level of historical volatility based on simple daily returns.
        Assigns a risk verdict (LOW_VOLATILITY, MODERATE_VOLATILITY, HIGH_VOLATILITY)
        based on predefined thresholds for the annualized volatility percentage.
        This agent focuses on the magnitude of price fluctuations as a risk measure.

    Metrics Calculated:
        - Daily Volatility (standard deviation of simple daily returns)
        - Annualized Volatility (daily volatility scaled by sqrt(252))

    Logic:
        1. Fetches historical price series.
        2. Calculates simple daily percentage returns.
        3. Calculates the standard deviation of these returns (daily volatility).
        4. Annualizes the daily volatility.
        5. Assigns a verdict based on the annualized volatility level compared to fixed thresholds (e.g., <20% = LOW, <40% = MODERATE, >=40% = HIGH).
        6. Confidence is adjusted based on the volatility level within the moderate range.

    Dependencies:
        - Requires historical price data (at least 2 data points).
        - Relies on `fetch_price_series` utility.

    Returns:
        dict: A dictionary containing the analysis results, including:
            - symbol (str): The input stock symbol.
            - verdict (str): 'LOW_VOLATILITY', 'MODERATE_VOLATILITY', 'HIGH_VOLATILITY', 'NO_DATA', or 'ERROR'.
            - confidence (float): Confidence score (0-1), adjusted based on volatility level.
            - value (float | None): The calculated annualized volatility percentage.
            - details (dict): Contains the annualized and daily volatility values.
            - error (str | None): Error message if execution failed.
            - agent_name (str): The name of the agent ('volatility_level_agent').
    """
    # Fetch price series
    prices = await fetch_price_series(symbol)
    # Use prices.empty for pandas Series check
    if prices is None or prices.empty or len(prices) < 2:
        return {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {"reason": f"Insufficient price data for {symbol}"},
            "agent_name": agent_name,
        }

    # Compute daily returns and volatility
    prices_array = np.array(prices)
    returns = np.diff(prices_array) / prices_array[:-1]
    if len(returns) == 0:
        return {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {"reason": "Could not calculate returns from price data"},
            "agent_name": agent_name,
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
            "daily_volatility": round(daily_volatility, 6),
        },
        "agent_name": agent_name,
    }

    return result
