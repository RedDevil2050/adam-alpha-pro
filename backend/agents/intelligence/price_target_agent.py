"""Auto-refactored price_target_agent agent."""

import numpy as np
from backend.utils.data_provider import fetch_price_series
from backend.agents.decorators import standard_agent_execution  # Import decorator

agent_name = "intelligence_price_target_agent"  # Renamed from price_target_agent
AGENT_CATEGORY = "intelligence"


# Apply the decorator
@standard_agent_execution(
    agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=3600
)
async def run(symbol: str, agent_outputs: dict = {}) -> dict:
    # Fetch price series (60 days) (Core Logic)
    prices = await fetch_price_series(symbol, source_preference=["api", "scrape"])
    if not prices or len(prices) < 2:
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
        x = np.arange(len(prices))
        # Handle case where all prices are the same (polyfit might warn/error)
        if np.all(prices == prices[0]):
            slope = 0
            intercept = prices[0]
            confidence = 0.1  # Low confidence if price is flat
            verdict = "FLAT"
            price_target = prices[0]  # Target is current price if flat
        else:
            slope, intercept = np.polyfit(x, prices, 1)
            price_target = (
                slope * (len(prices) + 30) + intercept
            )  # 30 days into the future

            # Normalize confidence based on slope
            mean_price = np.mean(prices)
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
