import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

import asyncio
from backend.utils.data_provider import fetch_alpha_vantage
from loguru import logger
from backend.agents.decorators import standard_agent_execution
from backend.config.settings import get_settings

agent_name = "dividend_agent"
AGENT_CATEGORY = "valuation"

# Define settings in settings.py (Manual Step - if thresholds needed)
# class DividendAgentSettings(BaseSettings):
#     SOME_THRESHOLD: float = 0.0 # Example if needed

@standard_agent_execution(agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=86400) # Longer TTL for less frequent data
async def run(symbol: str, agent_outputs: dict = None) -> dict:
    """
    Fetches and reports key dividend information for a stock symbol.

    Purpose:
        Provides fundamental dividend data like Dividend Per Share (DPS) and Ex-Dividend Date.
        This agent primarily serves as a data source for other agents like dividend_yield_agent.

    Metrics Calculated/Fetched:
        - Dividend Per Share (Annual)
        - Ex-Dividend Date
        - Dividend Yield (often provided alongside DPS)

    Logic:
        1. Fetches company overview data (e.g., from Alpha Vantage) which usually contains dividend information.
        2. Parses 'DividendPerShare', 'ExDividendDate', and 'DividendYield'.
        3. Validates the parsed data.
        4. Determines a simple verdict: 'PAYS_DIVIDEND' if DPS > 0, 'NO_DIVIDEND' if DPS is 0 or clearly indicated, 'NO_DATA' otherwise.
        5. Returns the fetched data in the details dictionary.

    Dependencies:
        - Requires a data provider function that returns overview/dividend data (e.g., `fetch_alpha_vantage`).

    Configuration Used (from settings.py):
        - None currently defined, but could be added if specific thresholds are needed.

    Return Structure:
        A dictionary containing:
        - symbol (str): The stock symbol.
        - verdict (str): 'PAYS_DIVIDEND', 'NO_DIVIDEND', 'NO_DATA'.
        - confidence (float): Fixed confidence score.
        - value (float | None): The Annual Dividend Per Share (DPS).
        - details (dict): Contains DPS, Ex-Date, Yield %, and data source.
        - agent_name (str): The name of this agent.
        - error (str | None): Error message if an issue occurred (handled by decorator).
    """
    # settings = get_settings() # Uncomment if settings are added
    # div_settings = settings.agent_settings.dividend # Example

    # Fetch overview data
    overview_data = await fetch_alpha_vantage("query", {"function": "OVERVIEW", "symbol": symbol})

    if not overview_data:
        return {
            "symbol": symbol, "verdict": "NO_DATA", "confidence": 0.0, "value": None,
            "details": {"reason": "Could not fetch overview data from Alpha Vantage"},
            "agent_name": agent_name
        }

    dps_str = overview_data.get("DividendPerShare")
    ex_date_str = overview_data.get("ExDividendDate")
    yield_str = overview_data.get("DividendYield")

    dps = None
    yield_pct = None
    ex_date = None
    data_source = "alpha_vantage_overview"

    # Parse DPS
    if dps_str and dps_str.lower() not in ["none", "-", ""]:
        try:
            dps = float(dps_str)
        except (ValueError, TypeError):
            logger.warning(f"[{agent_name}] Could not parse DividendPerShare for {symbol}: {dps_str}")

    # Parse Yield
    if yield_str and yield_str.lower() not in ["none", "-", ""]:
        try:
            # Yield is usually given as decimal, convert to percent for details consistency
            yield_pct = float(yield_str) * 100
        except (ValueError, TypeError):
            logger.warning(f"[{agent_name}] Could not parse DividendYield for {symbol}: {yield_str}")

    # Parse Ex-Date (keep as string for now)
    if ex_date_str and ex_date_str.lower() not in ["none", "-", ""]:
        ex_date = ex_date_str

    # Determine Verdict
    if dps is not None and dps > 0:
        verdict = "PAYS_DIVIDEND"
        confidence = 0.8
    elif dps is not None and dps == 0: # Explicitly zero
        verdict = "NO_DIVIDEND"
        confidence = 0.9
    elif dps_str and dps_str.lower() in ["0", "none"]: # String indicates zero/none
         verdict = "NO_DIVIDEND"
         confidence = 0.9
         dps = 0.0 # Set value to 0.0 for clarity
    else: # Cannot determine
        verdict = "NO_DATA"
        confidence = 0.1

    # Create result dictionary
    result = {
        "symbol": symbol,
        "verdict": verdict,
        "confidence": round(confidence, 4),
        "value": round(dps, 4) if dps is not None else None, # DPS as primary value
        "details": {
            "dividend_per_share": round(dps, 4) if dps is not None else None,
            "ex_dividend_date": ex_date,
            "dividend_yield_percent": round(yield_pct, 2) if yield_pct is not None else None,
            "data_source": data_source,
        },
        "agent_name": agent_name
    }
    return result