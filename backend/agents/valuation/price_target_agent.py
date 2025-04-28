import asyncio
from backend.utils.data_provider import fetch_alpha_vantage # Use standard fetcher
from loguru import logger
from backend.agents.decorators import standard_agent_execution
import math # Import math for isnan

agent_name = "valuation_price_target_agent"
AGENT_CATEGORY = "valuation"

@standard_agent_execution(agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=3600)
async def run(symbol: str, agent_outputs: dict = None) -> dict:
    # Boilerplate handled by decorator

    # Fetch overview data which contains AnalystTargetPrice
    overview_data = await fetch_alpha_vantage("query", {"function": "OVERVIEW", "symbol": symbol})

    if not overview_data:
        return {
            "symbol": symbol, "verdict": "NO_DATA", "confidence": 0.0, "value": None,
            "details": {"reason": "Could not fetch overview data from Alpha Vantage"},
            "agent_name": agent_name
        }

    # Extract Analyst Target Price
    target_price_str = overview_data.get("AnalystTargetPrice")
    target_price = None
    reason = "Analyst Target Price not available in overview data."

    if target_price_str and target_price_str.lower() not in ["none", "-", ""]:
        try:
            target_price = float(target_price_str)
            if math.isnan(target_price) or target_price <= 0:
                reason = f"Invalid Analyst Target Price found: {target_price_str}"
                target_price = None # Treat non-positive or NaN as unavailable
            else:
                reason = None # Successfully parsed
        except (ValueError, TypeError):
            reason = f"Could not parse Analyst Target Price: {target_price_str}"
            target_price = None

    # Check if target price was successfully extracted
    if target_price is None:
        return {
            "symbol": symbol,
            "verdict": "NO_ANALYST_TARGET",
            "confidence": 0.1, # Low confidence as no target is available
            "value": None,
            "details": {"reason": reason, "raw_value": target_price_str},
            "agent_name": agent_name
        }

    # Return success result with the analyst target price
    return {
        "symbol": symbol,
        "verdict": "ANALYST_TARGET_PRICE_AVAILABLE",
        "confidence": 0.8, # High confidence as it's directly from data source
        "value": round(target_price, 2),
        "details": {
            "analyst_target_price": round(target_price, 2),
            "data_source": "alpha_vantage_overview"
        },
        "agent_name": agent_name
    }

# Remove old run function if it exists
# from backend.utils.data_provider import fetch_eps, fetch_pe_target
# async def run(symbol: str, agent_outputs: dict = {}) -> dict:
#    # ... old logic ...
