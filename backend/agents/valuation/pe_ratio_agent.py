import asyncio
from backend.utils.data_provider import fetch_alpha_vantage # Use fetch_alpha_vantage
from loguru import logger
from backend.agents.decorators import standard_agent_execution # Import decorator
from backend.config.settings import get_settings # Import settings

agent_name = "pe_ratio_agent"
AGENT_CATEGORY = "valuation" # Define category for the decorator

@standard_agent_execution(agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=3600)
async def run(symbol: str, agent_outputs: dict = None) -> dict:
    """
    Calculates the Price-to-Earnings (P/E) ratio for a given stock symbol and assesses its valuation.

    Purpose:
        Determines the P/E ratio, a common metric used to assess if a stock is potentially
        undervalued, fairly valued, or overvalued relative to its earnings.

    Metrics Calculated:
        - P/E Ratio (Price per share / Earnings per share)

    Logic:
        1. Fetches company overview data from Alpha Vantage, which includes the P/E ratio.
        2. Parses the P/E ratio value. Handles cases where data is missing, 'None', or non-numeric.
        3. Compares the P/E ratio against configurable thresholds:
            - If PE <= 0: Verdict is 'NEGATIVE_EARNINGS'.
            - If 0 < PE <= THRESHOLD_UNDERVALUED: Verdict is 'UNDERVALUED'.
            - If THRESHOLD_UNDERVALUED < PE <= THRESHOLD_OVERVALUED: Verdict is 'FAIRLY_VALUED'.
            - If PE > THRESHOLD_OVERVALUED: Verdict is 'OVERVALUED'.
        4. Sets a fixed confidence score based on the verdict category.

    Dependencies:
        - Requires company overview data containing the P/E ratio (e.g., from Alpha Vantage).

    Configuration Used:
        - `settings.agent_settings.pe_ratio.THRESHOLD_UNDERVALUED`: Lower bound for 'FAIRLY_VALUED'.
        - `settings.agent_settings.pe_ratio.THRESHOLD_OVERVALUED`: Upper bound for 'FAIRLY_VALUED'.

    Return Structure:
        A dictionary containing:
        - symbol (str): The stock symbol.
        - verdict (str): 'UNDERVALUED', 'FAIRLY_VALUED', 'OVERVALUED', 'NEGATIVE_EARNINGS', 'NO_DATA', or 'INVALID_DATA'.
        - confidence (float): A fixed score based on the verdict category (0.0 to 1.0).
        - value (float | None): The calculated P/E ratio, or None if not available/applicable.
        - details (dict): Contains the raw P/E ratio and data source.
        - agent_name (str): The name of this agent.
        - error (str | None): Error message if an issue occurred (handled by decorator).
    """
    # Boilerplate handled by decorator

    # Fetch settings
    settings = get_settings()
    pe_settings = settings.agent_settings.pe_ratio

    # Fetch overview data which contains PE Ratio
    overview_data = await fetch_alpha_vantage("query", {"function": "OVERVIEW", "symbol": symbol})

    if not overview_data:
        return {
            "symbol": symbol, "verdict": "NO_DATA", "confidence": 0.0, "value": None,
            "details": {"reason": "Could not fetch overview data from Alpha Vantage"},
            "agent_name": agent_name
        }

    pe_ratio_str = overview_data.get("PERatio")
    pe_ratio = None

    if pe_ratio_str and pe_ratio_str.lower() not in ["none", "-", ""]:
        try:
            pe_ratio = float(pe_ratio_str)
        except (ValueError, TypeError):
            logger.warning(f"[{agent_name}] Could not parse PE ratio for {symbol}: {pe_ratio_str}")
            return {
                "symbol": symbol, "verdict": "INVALID_DATA", "confidence": 0.1, "value": None,
                "details": {"raw_pe_ratio": pe_ratio_str, "reason": "Could not parse PE ratio value"},
                "agent_name": agent_name
            }
    else:
        # Handle cases where PE is explicitly None or missing
        logger.warning(f"[{agent_name}] PE ratio not available for {symbol} in overview data.")
        return {
            "symbol": symbol, "verdict": "NO_DATA", "confidence": 0.5, "value": None, # Confidence 0.5 as we know it's missing
            "details": {"raw_pe_ratio": pe_ratio_str, "reason": "PE ratio value not provided or is None"},
            "agent_name": agent_name
        }

    # PE ratio is successfully parsed
    # Determine verdict based on configured thresholds
    if pe_ratio <= 0:
        # Negative or zero PE usually means negative earnings
        verdict = "NEGATIVE_EARNINGS"
        confidence = 0.7 # Confidence that the value indicates negative earnings
    elif pe_ratio <= pe_settings.THRESHOLD_UNDERVALUED:
        verdict = "UNDERVALUED" # Potentially undervalued
        confidence = 0.6
    elif pe_ratio <= pe_settings.THRESHOLD_OVERVALUED:
        verdict = "FAIRLY_VALUED" # Often considered reasonable range
        confidence = 0.5
    else: # PE > pe_settings.THRESHOLD_OVERVALUED
        verdict = "OVERVALUED" # Potentially overvalued, common for growth stocks
        confidence = 0.4

    # Create success result dictionary
    result = {
        "symbol": symbol,
        "verdict": verdict,
        "confidence": round(confidence, 4),
        "value": round(pe_ratio, 2), # Return the PE ratio
        "details": {
            "pe_ratio": round(pe_ratio, 2),
            "data_source": "alpha_vantage_overview",
            "threshold_undervalued": pe_settings.THRESHOLD_UNDERVALUED,
            "threshold_overvalued": pe_settings.THRESHOLD_OVERVALUED
        },
        "agent_name": agent_name
    }

    return result
