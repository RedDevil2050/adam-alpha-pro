from backend.utils.data_provider import fetch_price_series
import pandas as pd
from backend.agents.decorators import standard_agent_execution

agent_name = "MarketRegimeAgent"
AGENT_CATEGORY = "market"


@standard_agent_execution(agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=3600)
async def run(symbol: str, agent_outputs: dict = None) -> dict:
    # Fetch historical price series
    # Using a fixed date range here - consider making this dynamic or configurable if needed
    price_data = await fetch_price_series(symbol, "2023-01-01", "2023-12-31")
    prices_list = price_data.get("prices", [])

    if not prices_list or len(prices_list) < 2:
        # Return NO_DATA format
        return {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {},
        }

    prices = pd.Series(prices_list)

    # Calculate market regime (example logic)
    pct_change = prices.pct_change()
    volatility = pct_change.std()
    trend = pct_change.mean()

    # Handle potential NaN values if data is insufficient after pct_change
    if pd.isna(volatility) or pd.isna(trend):
        return {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {"reason": "Insufficient data for calculation"},
        }

    if volatility > 0.02 and trend > 0:
        regime = "Bullish"
        confidence = 0.8  # Example confidence
    elif volatility > 0.02 and trend < 0:
        regime = "Bearish"
        confidence = 0.8  # Example confidence
    else:
        regime = "Neutral"
        confidence = 0.6  # Example confidence

    # Return success result
    return {
        "symbol": symbol,
        "verdict": regime,
        "confidence": round(min(volatility * 50, 1.0), 4),  # Adjusted confidence calculation example
        "value": round(trend, 6),
        "details": {"volatility": round(volatility, 6), "trend": round(trend, 6)},
    }
