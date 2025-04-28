import asyncio
from backend.utils.data_provider import fetch_alpha_vantage
from loguru import logger
from backend.agents.decorators import standard_agent_execution
import math

agent_name = "valuation_price_to_book_agent"
AGENT_CATEGORY = "valuation"

@standard_agent_execution(agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=3600)
async def run(symbol: str, agent_outputs: dict = None) -> dict:
    # Boilerplate handled by decorator

    # Fetch overview data which contains PriceToBookRatio
    overview_data = await fetch_alpha_vantage("query", {"function": "OVERVIEW", "symbol": symbol})

    if not overview_data:
        return {
            "symbol": symbol, "verdict": "NO_DATA", "confidence": 0.0, "value": None,
            "details": {"reason": "Could not fetch overview data from Alpha Vantage"},
            "agent_name": agent_name
        }

    # Extract PriceToBookRatio
    pb_ratio_str = overview_data.get("PriceToBookRatio")
    pb_ratio = None
    reason = "PriceToBookRatio not available in overview data."

    if pb_ratio_str and pb_ratio_str.lower() not in ["none", "-", ""]:
        try:
            pb_ratio = float(pb_ratio_str)
            if math.isnan(pb_ratio) or pb_ratio <= 0:
                reason = f"Invalid PriceToBookRatio found: {pb_ratio_str}"
                pb_ratio = None # Treat non-positive or NaN as unavailable
            else:
                reason = None # Successfully parsed
        except (ValueError, TypeError):
            reason = f"Could not parse PriceToBookRatio: {pb_ratio_str}"
            pb_ratio = None

    # Check if P/B ratio was successfully extracted
    if pb_ratio is None:
        return {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.1, # Low confidence as P/B is unavailable
            "value": None,
            "details": {"reason": reason, "raw_value": pb_ratio_str},
            "agent_name": agent_name
        }

    # Determine verdict based on P/B ratio
    # Common interpretation: < 1 potentially undervalued, 1-3 fairly valued, > 3 potentially overvalued
    if pb_ratio < 1.0:
        verdict = "BUY"
        confidence = 0.7
        details = {"reason": f"P/B ratio ({pb_ratio:.2f}) is below 1, suggesting potential undervaluation."}
    elif pb_ratio <= 3.0:
        verdict = "HOLD"
        confidence = 0.6
        details = {"reason": f"P/B ratio ({pb_ratio:.2f}) is between 1 and 3, suggesting fair valuation."}
    else: # pb_ratio > 3.0
        verdict = "SELL"
        confidence = 0.7
        details = {"reason": f"P/B ratio ({pb_ratio:.2f}) is above 3, suggesting potential overvaluation."}

    details["pb_ratio"] = round(pb_ratio, 2)
    details["data_source"] = "alpha_vantage_overview"

    # Return success result with the P/B ratio and verdict
    return {
        "symbol": symbol,
        "verdict": verdict,
        "confidence": confidence,
        "value": round(pb_ratio, 2),
        "details": details,
        "agent_name": agent_name
    }

# Remove old placeholder run function
# async def run(symbol: str, agent_outputs: dict = {}) -> dict:
#    # ... old logic ...
