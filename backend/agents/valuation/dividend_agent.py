import asyncio
from backend.utils.data_provider import fetch_alpha_vantage, fetch_price_point
from loguru import logger
from backend.agents.decorators import standard_agent_execution # Import decorator

agent_name = "dividend_agent"
AGENT_CATEGORY = "valuation" # Define category for the decorator

@standard_agent_execution(agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=86400) # Cache for 24 hours
async def run(symbol: str, agent_outputs: dict = None) -> dict:
    # Boilerplate handled by decorator

    # Fetch overview data (contains dividend info) and price concurrently
    overview_task = fetch_alpha_vantage("query", {"function": "OVERVIEW", "symbol": symbol})
    price_task = fetch_price_point(symbol)
    overview_data, price_data = await asyncio.gather(overview_task, price_task)

    if not overview_data:
        return {
            "symbol": symbol, "verdict": "NO_DATA", "confidence": 0.0, "value": None,
            "details": {"reason": "Could not fetch overview data from Alpha Vantage"},
            "agent_name": agent_name
        }

    # Extract dividend data
    dividend_yield_str = overview_data.get("DividendYield")
    dividend_per_share_str = overview_data.get("DividendPerShare")
    ex_dividend_date_str = overview_data.get("ExDividendDate")
    dividend_pay_date_str = overview_data.get("DividendDate") # Note: AlphaVantage calls this DividendDate

    # Parse values, handle potential errors or "None" strings
    dividend_yield = None
    dividend_per_share = None

    try:
        if dividend_yield_str and dividend_yield_str.lower() not in ["none", "-", ""]:
            dividend_yield = float(dividend_yield_str)
    except (ValueError, TypeError):
        logger.warning(f"Could not parse DividendYield for {symbol}: {dividend_yield_str}")

    try:
        if dividend_per_share_str and dividend_per_share_str.lower() not in ["none", "-", ""]:
            dividend_per_share = float(dividend_per_share_str)
    except (ValueError, TypeError):
        logger.warning(f"Could not parse DividendPerShare for {symbol}: {dividend_per_share_str}")

    # Basic check if the company pays dividends
    pays_dividends = (dividend_yield is not None and dividend_yield > 0) or \
                     (dividend_per_share is not None and dividend_per_share > 0)

    if not pays_dividends:
        verdict = "NO_DIVIDEND"
        confidence = 0.9 # High confidence if data indicates no dividend
        value = 0.0
    else:
        # Simple verdict based on yield (example thresholds)
        if dividend_yield is not None:
            value = dividend_yield * 100 # Use yield percentage as value
            if dividend_yield > 0.04: # > 4% yield
                verdict = "HIGH_YIELD"
                confidence = 0.8
            elif dividend_yield > 0.015: # > 1.5% yield
                verdict = "MODERATE_YIELD"
                confidence = 0.6
            else: # <= 1.5% yield
                verdict = "LOW_YIELD"
                confidence = 0.5
        else:
            # If yield is missing but DPS exists, cannot determine yield-based verdict
            verdict = "PAYS_DIVIDEND_UNKNOWN_YIELD"
            confidence = 0.4
            value = None # Cannot determine yield value

    # Prepare details
    details = {
        "dividend_yield_percent": round(dividend_yield * 100, 2) if dividend_yield is not None else None,
        "dividend_per_share": dividend_per_share,
        "ex_dividend_date": ex_dividend_date_str if ex_dividend_date_str and ex_dividend_date_str.lower() != "none" else None,
        "dividend_pay_date": dividend_pay_date_str if dividend_pay_date_str and dividend_pay_date_str.lower() != "none" else None,
        "pays_dividends": pays_dividends
    }

    # Create success result dictionary
    result = {
        "symbol": symbol,
        "verdict": verdict,
        "confidence": round(confidence, 4),
        "value": round(value, 2) if value is not None else None, # Report yield percentage
        "details": details,
        "agent_name": agent_name
    }

    return result