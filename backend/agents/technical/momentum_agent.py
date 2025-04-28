import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

import pandas as pd
import numpy as np
from backend.utils.data_provider import fetch_historical_price_series
from backend.agents.decorators import standard_agent_execution
from backend.config.settings import get_settings
from loguru import logger
import asyncio # Import asyncio

agent_name = "momentum_agent"
AGENT_CATEGORY = "technical"

@standard_agent_execution(agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=3600)
async def run(symbol: str, agent_outputs: dict = None) -> dict:
    """
    Calculates price momentum over various lookback periods for a given stock symbol.

    Purpose:
        Evaluates the trend strength of a stock's price movement based on its past performance.
        Positive momentum suggests an upward trend, while negative momentum suggests a downward trend.

    Metrics Calculated:
        - Total return over configured lookback periods (e.g., 1, 3, 6, 12 months).
        - Average momentum across the specified lookback periods.

    Logic:
        1. Fetches historical price data for the symbol, ensuring enough data for the longest lookback period.
        2. Calculates the total percentage return for each lookback period defined in the settings.
        3. Calculates the simple average of the valid returns calculated in the previous step.
        4. Assigns a verdict based on the average momentum compared to configured thresholds:
           'STRONG_POSITIVE_MOMENTUM', 'POSITIVE_MOMENTUM', 'NEGATIVE_MOMENTUM', 'STRONG_NEGATIVE_MOMENTUM'.
        5. Sets a fixed confidence score based on the verdict.

    Dependencies:
        - Requires historical price data (`fetch_historical_price_series`).

    Configuration Used (from settings.py):
        - `agent_settings.momentum.LOOKBACK_PERIODS`: List of lookback periods in trading days (e.g., [21, 63, 126, 252]).
        - `agent_settings.momentum.THRESHOLD_STRONG_POSITIVE`: Lower bound for 'STRONG_POSITIVE_MOMENTUM' verdict (average return).
        - `agent_settings.momentum.THRESHOLD_STRONG_NEGATIVE`: Upper bound for 'STRONG_NEGATIVE_MOMENTUM' verdict (average return).

    Returns:
        dict: A dictionary containing the analysis results, including:
            - symbol (str): The input stock symbol.
            - verdict (str): Momentum verdict.
            - confidence (float): Fixed confidence score based on verdict.
            - value (float | None): The average momentum percentage.
            - details (dict): Contains individual period returns, average momentum, and configuration used.
            - error (str | None): Error message if execution failed.
            - agent_name (str): The name of the agent.
    """
    settings = get_settings()
    mom_settings = settings.agent_settings.momentum

    if not mom_settings.LOOKBACK_PERIODS:
        logger.warning(f"[{agent_name}] No lookback periods defined in settings for {symbol}.")
        return {
            "symbol": symbol, "verdict": "NO_DATA", "confidence": 0.0, "value": None,
            "details": {"reason": "Lookback periods not configured"}, "agent_name": agent_name
        }

    max_lookback = max(mom_settings.LOOKBACK_PERIODS)
    # Fetch slightly more data than needed for buffer
    required_years = int(max_lookback / 252) + 1

    try:
        historical_prices = await fetch_historical_price_series(symbol, years=required_years)
    except Exception as fetch_err:
        logger.error(f"[{agent_name}] Error fetching historical prices for {symbol}: {fetch_err}")
        return {
            "symbol": symbol, "verdict": "NO_DATA", "confidence": 0.0, "value": None,
            "details": {"reason": f"Failed to fetch historical prices: {fetch_err}"},
            "agent_name": agent_name
        }

    # Validate data
    if historical_prices is None or not isinstance(historical_prices, pd.Series) or historical_prices.empty:
         return {
            "symbol": symbol, "verdict": "NO_DATA", "confidence": 0.0, "value": None,
            "details": {"reason": "Historical price data is missing or invalid"}, "agent_name": agent_name
        }

    if len(historical_prices) <= max_lookback:
        return {
            "symbol": symbol, "verdict": "NO_DATA", "confidence": 0.0, "value": None,
            "details": {"reason": f"Insufficient historical data points ({len(historical_prices)}) for longest lookback ({max_lookback})"},
            "agent_name": agent_name
        }

    # Calculate Returns
    returns = {}
    details = {}
    latest_price = historical_prices.iloc[-1]

    for period in mom_settings.LOOKBACK_PERIODS:
        try:
            # Ensure index exists before accessing
            if -1 - period >= -len(historical_prices):
                past_price = historical_prices.iloc[-1 - period]
                if pd.notna(past_price) and past_price > 0:
                    period_return = (latest_price / past_price) - 1
                    returns[f'{period}d'] = period_return
                    details[f'return_{period}d_pct'] = round(period_return * 100, 2)
                else:
                    details[f'return_{period}d_pct'] = None # Invalid past price
            else:
                 details[f'return_{period}d_pct'] = None # Not enough data points historically
        except IndexError:
             details[f'return_{period}d_pct'] = None # Should not happen with length check, but safety

    # Calculate Average Momentum
    valid_returns = [r for r in returns.values() if r is not None and pd.notna(r)]
    average_momentum = np.mean(valid_returns) if valid_returns else None
    details['average_momentum_pct'] = round(average_momentum * 100, 2) if average_momentum is not None else None

    # Determine Verdict
    if average_momentum is None:
        verdict = "NO_DATA" # Could not calculate any valid returns
        confidence = 0.0
        details["reason"] = "Could not calculate momentum for any lookback period."
    elif average_momentum > mom_settings.THRESHOLD_STRONG_POSITIVE:
        verdict = "STRONG_POSITIVE_MOMENTUM"
        confidence = 0.7
    elif average_momentum < mom_settings.THRESHOLD_STRONG_NEGATIVE:
        verdict = "STRONG_NEGATIVE_MOMENTUM"
        confidence = 0.7
    elif average_momentum > 0: # Positive but not strong
        verdict = "POSITIVE_MOMENTUM"
        confidence = 0.5
    else: # Negative but not strong
        verdict = "NEGATIVE_MOMENTUM"
        confidence = 0.5

    # Add config to details
    details["config_used"] = {
        "lookback_periods": mom_settings.LOOKBACK_PERIODS,
        "threshold_strong_positive": mom_settings.THRESHOLD_STRONG_POSITIVE,
        "threshold_strong_negative": mom_settings.THRESHOLD_STRONG_NEGATIVE
    }
    details["data_source"] = "historical_prices"

    # Return result
    result = {
        "symbol": symbol,
        "verdict": verdict,
        "confidence": round(confidence, 4),
        "value": round(average_momentum * 100, 2) if average_momentum is not None else None, # Return avg momentum %
        "details": details,
        "agent_name": agent_name
    }
    return result
