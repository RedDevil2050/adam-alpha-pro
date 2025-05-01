import asyncio
from backend.utils.data_provider import fetch_company_info, fetch_price_point # Use unified provider
from loguru import logger
from backend.agents.decorators import standard_agent_execution
import math

agent_name = "valuation_price_to_book_agent"
AGENT_CATEGORY = "valuation"


@standard_agent_execution(
    agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=3600
)
async def run(symbol: str, agent_outputs: dict = None) -> dict:
    # Boilerplate handled by decorator

    # Fetch necessary data using unified provider
    company_info_task = fetch_company_info(symbol)
    price_data_task = fetch_price_point(symbol)
    company_info, price_data = await asyncio.gather(company_info_task, price_data_task)

    if not company_info or not price_data or "error" in price_data:
        reason = "Could not fetch required data (company info or price)."
        if price_data and "error" in price_data:
            reason += f" Price fetch error: {price_data['error']}"
        logger.warning(f"[{agent_name}] {reason} for {symbol}")
        return {
            "symbol": symbol, "verdict": "NO_DATA", "confidence": 0.0, "value": None,
            "details": {"reason": reason}, "agent_name": agent_name,
            "error": "Could not fetch required data (company info or price)."
        }

    bvps_str = company_info.get("BookValuePerShare") # Key might differ based on provider
    current_price = price_data.get("price")

    if current_price is None:
         logger.warning(f"[{agent_name}] Current price not available for {symbol}")
         return {
             "symbol": symbol, "verdict": "NO_DATA", "confidence": 0.0, "value": None,
             "details": {"reason": "Current price not available"}, "agent_name": agent_name,
             "error": "Current price not available"
         }

    bvps = None
    # ... parsing logic for bvps_str and current_price ...
    try:
        bvps = float(bvps_str)
        current_price = float(current_price)
        if current_price <= 0:
             raise ValueError("Price must be positive") # Price shouldn't be zero/negative
    except (ValueError, TypeError, AttributeError):
        logger.warning(
            f"[{agent_name}] Could not parse BVPS ('{bvps_str}') or price ('{current_price}') for {symbol}"
        )
        return {
            "symbol": symbol, "verdict": "INVALID_DATA", "confidence": 0.1, "value": None,
            "details": {"raw_bvps": bvps_str, "raw_price": current_price, "reason": "Could not parse BVPS or price"},
            "agent_name": agent_name,
            "error": "Could not parse BVPS or price"
        }

    if bvps is None: # Should be caught above, but double-check
         logger.warning(f"[{agent_name}] BVPS is None after parsing for {symbol}")
         return {
             "symbol": symbol, "verdict": "INVALID_DATA", "confidence": 0.1, "value": None,
             "details": {"reason": "BVPS became None unexpectedly"}, "agent_name": agent_name,
             "error": "BVPS became None unexpectedly"
         }

    if bvps <= 0:
        logger.info(f"[{agent_name}] Book Value Per Share is zero or negative ({bvps}) for {symbol}. P/B not meaningful.")
        return {
            "symbol": symbol, "verdict": "NEGATIVE_OR_ZERO_BV", "confidence": 0.8, "value": None,
            "details": {"reason": "Book Value Per Share <= 0", "bvps": bvps, "price": current_price},
            "agent_name": agent_name,
            "error": "Book Value Per Share <= 0"
        }

    # Calculate Price-to-Book (P/B) Ratio
    pb_ratio = current_price / bvps

    # Determine verdict based on P/B ratio (example thresholds)
    # Common interpretation: < 1 potentially undervalued, 1-3 fairly valued, > 3 potentially overvalued
    if pb_ratio < 1.0:
        verdict = "BUY"
        confidence = 0.7
        details = {
            "reason": f"P/B ratio ({pb_ratio:.2f}) is below 1, suggesting potential undervaluation."
        }
    elif pb_ratio <= 3.0:
        verdict = "HOLD"
        confidence = 0.6
        details = {
            "reason": f"P/B ratio ({pb_ratio:.2f}) is between 1 and 3, suggesting fair valuation."
        }
    else:  # pb_ratio > 3.0
        verdict = "SELL"
        confidence = 0.7
        details = {
            "reason": f"P/B ratio ({pb_ratio:.2f}) is above 3, suggesting potential overvaluation."
        }

    details["pb_ratio"] = round(pb_ratio, 2)
    details["data_source"] = "unified_provider" # Adjust as needed

    # Return success result with the P/B ratio and verdict
    return {
        "symbol": symbol,
        "verdict": verdict,
        "confidence": round(confidence, 4),
        "value": round(pb_ratio, 4),
        "details": {
            "price_to_book": round(pb_ratio, 4),
            "current_price": round(current_price, 4),
            "book_value_per_share": round(bvps, 4),
            "data_source": "unified_provider", # Adjust as needed
        },
        "agent_name": agent_name,
        "error": None
    }


# Remove old placeholder run function
# async def run(symbol: str, agent_outputs: dict = {}) -> dict:
#    # ... old logic ...
