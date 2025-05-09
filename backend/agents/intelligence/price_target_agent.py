"""Auto-refactored price_target_agent agent."""

import pandas as pd
import numpy as np
from backend.utils.data_provider import fetch_price_series
from backend.agents.decorators import standard_agent_execution  # Import decorator

agent_name = "price_target_agent" # Changed to match expected name from logs
AGENT_CATEGORY = "intelligence"


# Apply the decorator
@standard_agent_execution(
    agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=3600
)
async def run(symbol: str, agent_outputs: dict = {}) -> dict:
    # Fetch price series (60 days) (Core Logic)
    price_data = await fetch_price_series(symbol, source_preference=["api", "scrape"])

    prices_array = None
    if isinstance(price_data, pd.Series):
        if not price_data.empty:
            prices_array = price_data.to_numpy()
    elif isinstance(price_data, np.ndarray) and price_data.ndim == 1:
        prices_array = price_data

    if prices_array is None or len(prices_array) < 2:
        # Return NO_DATA format
        return {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {},
        }
    else:
        # Calculate price target using linear regression (Core Logic)
        x = np.arange(len(prices_array))
        # Handle case where all prices are the same (polyfit might warn/error)
        if np.all(prices_array == prices_array[0]):
            slope = 0
            intercept = prices_array[0]
            confidence = 0.1  # Low confidence if price is flat
            verdict = "FLAT"
            price_target = prices_array[0]  # Target is current price if flat
        else:
            slope, intercept = np.polyfit(x, prices_array, 1)
            price_target = (
                slope * (len(prices_array) + 30) + intercept
            )  # 30 days into the future

            # Normalize confidence based on slope
            mean_price = np.mean(prices_array)
            if mean_price == 0:
                confidence = 0.0  # Avoid division by zero
            else:
                confidence = min(abs(slope) / mean_price, 1.0)

            verdict = "UPTREND" if slope > 0 else "DOWNTREND"

        # Return success result (Core Logic)
        result = {
            "symbol": symbol,
            "verdict": verdict,
            "confidence": round(confidence, 4),
            "value": round(price_target, 2),
            "details": {"slope": round(slope, 4), "intercept": round(intercept, 4)},
        }
        return result
