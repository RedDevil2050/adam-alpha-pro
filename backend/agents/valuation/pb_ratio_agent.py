import asyncio
from backend.utils.data_provider import fetch_alpha_vantage # Use fetch_alpha_vantage
from loguru import logger
from backend.agents.decorators import standard_agent_execution # Import decorator
# TODO: Import get_settings and add PbRatioAgentSettings to settings.py
# from backend.config.settings import get_settings

agent_name = "pb_ratio_agent"
AGENT_CATEGORY = "valuation" # Define category for the decorator

@standard_agent_execution(agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=3600)
async def run(symbol: str, agent_outputs: dict = None) -> dict:
    """
    Calculates the Price-to-Book (P/B) ratio for a given stock symbol and assesses its valuation.

    Purpose:
        Determines the P/B ratio, comparing a company's market capitalization to its book value.
        It helps assess if a stock is potentially undervalued or overvalued relative to its net asset value.

    Metrics Calculated:
        - P/B Ratio (Market Price per Share / Book Value per Share)

    Logic:
        1. Fetches company overview data from Alpha Vantage, which includes the P/B ratio.
        2. Parses the P/B ratio value. Handles cases where data is missing, 'None', or non-numeric.
        3. Compares the P/B ratio against configurable thresholds (THRESHOLD_LOW_PB, THRESHOLD_HIGH_PB):
            - If PB <= 0: Verdict is 'NEGATIVE_OR_ZERO_BV' (indicates negative book value).
            - If 0 < PB <= THRESHOLD_LOW_PB: Verdict is 'UNDERVALUED'.
            - If THRESHOLD_LOW_PB < PB <= THRESHOLD_HIGH_PB: Verdict is 'FAIRLY_VALUED'.
            - If PB > THRESHOLD_HIGH_PB: Verdict is 'OVERVALUED'.
        4. Sets a fixed confidence score based on the verdict category.

    Dependencies:
        - Requires company overview data containing the P/B ratio (e.g., from Alpha Vantage).

    Configuration Used (Requires manual addition to settings.py):
        - `settings.agent_settings.pb_ratio.THRESHOLD_LOW_PB`: Upper bound for 'UNDERVALUED'.
        - `settings.agent_settings.pb_ratio.THRESHOLD_HIGH_PB`: Upper bound for 'FAIRLY_VALUED'.

    Return Structure:
        A dictionary containing:
        - symbol (str): The stock symbol.
        - verdict (str): 'UNDERVALUED', 'FAIRLY_VALUED', 'OVERVALUED', 'NEGATIVE_OR_ZERO_BV', 'NO_DATA', or 'INVALID_DATA'.
        - confidence (float): A fixed score based on the verdict category (0.0 to 1.0).
        - value (float | None): The calculated P/B ratio, or None if not available/applicable.
        - details (dict): Contains the raw P/B ratio, data source, and configured thresholds.
        - agent_name (str): The name of this agent.
        - error (str | None): Error message if an issue occurred (handled by decorator).
    """
    # Boilerplate handled by decorator
    # TODO: Fetch settings
    # settings = get_settings()
    # pb_settings = settings.agent_settings.pb_ratio
    # Define thresholds directly for now, replace with settings later
    THRESHOLD_LOW_PB = 1.0
    THRESHOLD_HIGH_PB = 3.0

    # Fetch overview data which contains Price/Book ratio
    overview_data = await fetch_alpha_vantage("query", {"function": "OVERVIEW", "symbol": symbol})

    if not overview_data:
        return {
            "symbol": symbol, "verdict": "NO_DATA", "confidence": 0.0, "value": None,
            "details": {"reason": "Could not fetch overview data from Alpha Vantage"},
            "agent_name": agent_name
        }

    pb_ratio_str = overview_data.get("PriceToBookRatio")
    pb_ratio = None

    if pb_ratio_str and pb_ratio_str.lower() not in ["none", "-", ""]:
        try:
            pb_ratio = float(pb_ratio_str)
        except (ValueError, TypeError):
            logger.warning(f"[{agent_name}] Could not parse P/B ratio for {symbol}: {pb_ratio_str}")
            return {
                "symbol": symbol, "verdict": "INVALID_DATA", "confidence": 0.1, "value": None,
                "details": {"raw_pb_ratio": pb_ratio_str, "reason": "Could not parse P/B ratio value"},
                "agent_name": agent_name
            }
    else:
        # Handle cases where P/B is explicitly None or missing
        logger.warning(f"[{agent_name}] P/B ratio not available for {symbol} in overview data.")
        return {
            "symbol": symbol, "verdict": "NO_DATA", "confidence": 0.5, "value": None, # Confidence 0.5 as we know it's missing
            "details": {"raw_pb_ratio": pb_ratio_str, "reason": "P/B ratio value not provided or is None"},
            "agent_name": agent_name
        }

    # P/B ratio is successfully parsed
    # Determine verdict based on standardized thresholds
    if pb_ratio <= 0:
        # Negative or zero P/B is unusual and likely indicates negative book value (equity)
        verdict = "NEGATIVE_OR_ZERO_BV" # Specific case
        confidence = 0.7 # Confidence that the value is problematic
    elif pb_ratio <= THRESHOLD_LOW_PB: # Use threshold
        verdict = "UNDERVALUED" # Standardized verdict
        confidence = 0.6 # Moderate confidence, needs context
    elif pb_ratio <= THRESHOLD_HIGH_PB: # Use threshold
        verdict = "FAIRLY_VALUED" # Standardized verdict
        confidence = 0.5
    else: # P/B > THRESHOLD_HIGH_PB
        verdict = "OVERVALUED" # Standardized verdict
        confidence = 0.4

    # Create success result dictionary
    result = {
        "symbol": symbol,
        "verdict": verdict,
        "confidence": round(confidence, 4),
        "value": round(pb_ratio, 2), # Return the P/B ratio
        "details": {
            "pb_ratio": round(pb_ratio, 2),
            "data_source": "alpha_vantage_overview",
            # TODO: Add thresholds from settings to details
            "threshold_undervalued": THRESHOLD_LOW_PB, # Using placeholder value for now
            "threshold_overvalued": THRESHOLD_HIGH_PB  # Using placeholder value for now
        },
        "agent_name": agent_name
    }

    return result
