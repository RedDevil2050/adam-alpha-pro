import asyncio
from backend.utils.data_provider import fetch_price_point, fetch_company_info # Updated imports
from loguru import logger
from backend.agents.decorators import standard_agent_execution # Import decorator
import math # Import math for isnan

agent_name = "price_to_sales_agent"
AGENT_CATEGORY = "valuation" # Define category

@standard_agent_execution(
    agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=3600
)
async def run(symbol: str, agent_outputs: dict = None) -> dict:
    # Boilerplate handled by decorator

    # Fetch Price and Company Info (Revenue, Shares Outstanding)
    price_task = fetch_price_point(symbol)
    company_info_task = fetch_company_info(symbol)
    price_data, company_info = await asyncio.gather(price_task, company_info_task)

    current_price = price_data.get("price") if price_data else None

    if not company_info or current_price is None:
        reason = "Could not fetch required data (company info or price)."
        if current_price is None:
            reason = "Could not fetch current price." # Removed backslash
        elif not company_info:
            reason = "Could not fetch company info." # Removed backslash
        logger.warning(f"[{agent_name}] {reason} for {symbol}") # Corrected f-string syntax
        return {
            "symbol": symbol, "verdict": "NO_DATA", "confidence": 0.0, "value": None,
            "details": {"reason": reason}, "agent_name": agent_name,
        }

    # Extract Revenue TTM and Shares Outstanding
    revenue_ttm_str = company_info.get("RevenueTTM")
    shares_outstanding_str = company_info.get("SharesOutstanding")

    revenue_ttm = None
    shares_outstanding = None

    try:
        if revenue_ttm_str and revenue_ttm_str.lower() not in ["none", "-", ""]:
            revenue_ttm = float(revenue_ttm_str)
        if shares_outstanding_str and shares_outstanding_str.lower() not in ["none", "-", ""]:
            shares_outstanding = float(shares_outstanding_str)
        current_price = float(current_price) # Ensure price is float

        if revenue_ttm is None or revenue_ttm <= 0:
             raise ValueError("Revenue must be positive")
        if shares_outstanding is None or shares_outstanding <= 0:
             raise ValueError("Shares Outstanding must be positive")
        if current_price <= 0:
             raise ValueError("Price must be positive")

    except (ValueError, TypeError, AttributeError) as e:
        logger.warning(
            f"[{agent_name}] Could not parse required data for P/S calculation for {symbol}: {e}"
            f" (Revenue: '{revenue_ttm_str}', Shares: '{shares_outstanding_str}', Price: '{current_price}')"
        )
        return {
            "symbol": symbol, "verdict": "INVALID_DATA", "confidence": 0.1, "value": None,
            "details": {
                "raw_revenue_ttm": revenue_ttm_str,
                "raw_shares_outstanding": shares_outstanding_str,
                "raw_price": price_data.get("price"), # Use original price string if parsing failed
                "reason": f"Could not parse required data: {e}"
            },
            "agent_name": agent_name,
        }

    # Calculate Sales Per Share (SPS)
    sales_per_share = revenue_ttm / shares_outstanding

    # Calculate Price-to-Sales (P/S) Ratio
    ps_ratio = current_price / sales_per_share

    # Determine verdict based on P/S ratio (example thresholds)
    # Lower is generally better. Industry context matters.
    # Example: < 1 potentially undervalued, 1-2 reasonable, > 4 potentially overvalued (tech might be higher)
    if ps_ratio < 1.0:
        verdict = "LOW_PS" # Potentially Undervalued
        confidence = 0.7
    elif ps_ratio < 2.0:
        verdict = "MODERATE_PS" # Reasonable
        confidence = 0.5
    elif ps_ratio < 4.0:
        verdict = "HIGH_PS" # Potentially Overvalued
        confidence = 0.4
    else: # ps_ratio >= 4.0
        verdict = "VERY_HIGH_PS" # Likely Overvalued (or high growth expected)
        confidence = 0.3

    return {
        "symbol": symbol,
        "verdict": verdict,
        "confidence": round(confidence, 4),
        "value": round(ps_ratio, 2),
        "details": {
            "price_to_sales_ratio": round(ps_ratio, 2),
            "current_price": round(current_price, 2),
            "sales_per_share": round(sales_per_share, 4),
            "revenue_ttm": revenue_ttm,
            "shares_outstanding": shares_outstanding,
            "data_source": "company_info + price_point"
        },
        "agent_name": agent_name,
    }
