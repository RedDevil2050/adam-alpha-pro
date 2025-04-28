import asyncio
from backend.utils.data_provider import fetch_alpha_vantage  # Use fetch_alpha_vantage
from loguru import logger
from backend.agents.decorators import standard_agent_execution  # Import decorator
from backend.config.settings import get_settings  # Added import

agent_name = "peg_ratio_agent"
AGENT_CATEGORY = "valuation"  # Define category for the decorator


@standard_agent_execution(
    agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=3600
)
async def run(symbol: str, agent_outputs: dict = None) -> dict:
    """
    Calculates the Price/Earnings-to-Growth (PEG) ratio for a given stock symbol and assesses its valuation relative to growth expectations.

    Purpose:
        Determines the PEG ratio, which adjusts the P/E ratio by factoring in the expected earnings growth rate.
        It helps assess if a stock's price is justified by its earnings growth prospects.
        A PEG ratio around 1 is often considered fairly valued, < 1 potentially undervalued, and > 1 potentially overvalued.

    Metrics Calculated:
        - PEG Ratio (P/E Ratio / Annual EPS Growth Rate)

    Logic:
        1. Fetches company overview data from Alpha Vantage, which may include a pre-calculated PEG ratio.
        2. Attempts to parse the provided PEG ratio. Handles cases where data is missing, 'None', or non-numeric.
        3. (Future Enhancement: If PEG is not provided, it could be calculated using P/E ratio (also from overview) and an externally sourced EPS growth rate. This is not currently implemented due to lack of a reliable growth rate source in the overview data.)
        4. Compares the PEG ratio against configurable thresholds (THRESHOLD_LOW_PEG, THRESHOLD_HIGH_PEG):
            - If PEG <= 0: Verdict is 'NEGATIVE_OR_ZERO_PEG' (indicates negative earnings or growth).
            - If 0 < PEG < THRESHOLD_LOW_PEG: Verdict is 'UNDERVALUED'.
            - If THRESHOLD_LOW_PEG <= PEG <= THRESHOLD_HIGH_PEG: Verdict is 'FAIRLY_VALUED'.
            - If PEG > THRESHOLD_HIGH_PEG: Verdict is 'OVERVALUED'.
        5. Sets a fixed confidence score based on the verdict category.

    Dependencies:
        - Requires company overview data containing the PEG ratio (e.g., from Alpha Vantage).
        - (Calculation fallback would require P/E ratio and a reliable EPS growth rate source).

    Configuration Used (from settings.py -> AgentSettings -> PegRatioAgentSettings): # Updated docstring section
        - `THRESHOLD_LOW_PEG`: Upper bound for 'UNDERVALUED'.
        - `THRESHOLD_HIGH_PEG`: Upper bound for 'FAIRLY VALUED'.

    Return Structure:
        A dictionary containing:
        - symbol (str): The stock symbol.
        - verdict (str): 'UNDERVALUED', 'FAIRLY_VALUED', 'OVERVALUED', 'NEGATIVE_OR_ZERO_PEG', 'NO_DATA', or 'INVALID_DATA'.
        - confidence (float): A fixed score based on the verdict category (0.0 to 1.0).
        - value (float | None): The calculated/provided PEG ratio, or None if not available/applicable.
        - details (dict): Contains the raw PEG/PE ratios, data source, and configured thresholds.
        - agent_name (str): The name of this agent.
        - error (str | None): Error message if an issue occurred (handled by decorator).
    """
    # Fetch settings
    settings = get_settings()
    peg_settings = settings.agent_settings.peg_ratio

    # Thresholds now come from settings
    # THRESHOLD_LOW_PEG = 1.0 # Removed hardcoded value
    # THRESHOLD_HIGH_PEG = 2.0 # Removed hardcoded value

    # Fetch overview data which contains PE Ratio and PEG Ratio
    # Note: Alpha Vantage provides PEG directly, but also PE and Analyst Target Price (which might imply growth)
    # We will prioritize the directly provided PEG, but calculate if needed/possible from PE and Growth Estimate
    overview_data = await fetch_alpha_vantage(
        "query", {"function": "OVERVIEW", "symbol": symbol}
    )

    if not overview_data:
        return {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {"reason": "Could not fetch overview data from Alpha Vantage"},
            "agent_name": agent_name,
        }

    peg_ratio_str = overview_data.get("PEGRatio")
    pe_ratio_str = overview_data.get("PERatio")
    # Growth rate isn't directly in overview, often needs separate source or estimation
    # Alpha Vantage doesn't reliably provide a standard EPS growth rate here.
    # We will rely on the provided PEG ratio first.

    peg_ratio = None
    data_source = "alpha_vantage_overview_peg"

    # 1. Try using the directly provided PEG Ratio
    if peg_ratio_str and peg_ratio_str.lower() not in ["none", "-", "", "0"]:
        try:
            peg_ratio = float(peg_ratio_str)
            logger.info(
                f"[{agent_name}] Using directly provided PEG ratio for {symbol}: {peg_ratio}"
            )
        except (ValueError, TypeError):
            logger.warning(
                f"[{agent_name}] Could not parse provided PEG ratio for {symbol}: {peg_ratio_str}. Will attempt calculation if possible."
            )
            peg_ratio = None  # Ensure it's None if parsing failed

    # 2. Fallback: Calculate PEG if PE is available (Requires external growth rate source - NOT IMPLEMENTED here)
    # This section is commented out as reliable growth rate isn't in overview
    # if peg_ratio is None:
    #     logger.info(f"[{agent_name}] Provided PEG not available/parseable for {symbol}. Calculation fallback not implemented due to missing growth rate.")
    # pe_ratio = None
    # growth_rate = None # Needs to be fetched from another source
    # data_source = "calculated (fallback - growth rate source needed)"
    # if pe_ratio_str and pe_ratio_str.lower() not in ["none", "-", ""]:
    #     try:
    #         pe_ratio = float(pe_ratio_str)
    #     except (ValueError, TypeError):
    #         pe_ratio = None
    #
    # # Placeholder: Fetch or estimate growth rate (e.g., from analyst estimates)
    # # growth_rate = await fetch_some_growth_rate_source(symbol) # Example
    #
    # if pe_ratio and growth_rate and growth_rate > 0:
    #     peg_ratio = pe_ratio / (growth_rate * 100) # Assuming growth rate is percentage e.g., 15 for 15%
    #     logger.info(f"[{agent_name}] Calculated PEG ratio for {symbol}: {peg_ratio}")
    # else:
    #     logger.warning(f"[{agent_name}] Cannot calculate PEG for {symbol} due to missing PE ({pe_ratio}) or growth rate ({growth_rate}).")

    # 3. Check if we have a valid PEG ratio
    if peg_ratio is None:
        details = {
            "raw_peg_ratio": peg_ratio_str,
            "raw_pe_ratio": pe_ratio_str,
            "reason": "PEG ratio not provided by Alpha Vantage or could not be parsed. Fundamental calculation fallback not implemented due to missing growth rate source.",
        }
        return {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.1,
            "value": None,
            "details": details,
            "agent_name": agent_name,
        }

    # 4. Determine Verdict based on standardized PEG ratio thresholds
    if peg_ratio <= 0:
        # Negative PEG usually means negative earnings (negative PE) or zero/negative growth
        verdict = "NEGATIVE_OR_ZERO_PEG"  # Specific case
        confidence = 0.6  # Confidence that the value is problematic or indicates negative earnings/growth
    elif peg_ratio < peg_settings.THRESHOLD_LOW_PEG:  # Use setting
        verdict = (
            "UNDERVALUED"  # Standardized verdict (potentially high growth for price)
        )
        confidence = 0.7
    elif peg_ratio <= peg_settings.THRESHOLD_HIGH_PEG:  # Use setting
        verdict = "FAIRLY_VALUED"  # Standardized verdict
        confidence = 0.5
    else:  # peg_ratio > peg_settings.THRESHOLD_HIGH_PEG
        verdict = (
            "OVERVALUED"  # Standardized verdict (potentially low growth for price)
        )
        confidence = 0.4

    # Create success result dictionary
    result = {
        "symbol": symbol,
        "verdict": verdict,
        "confidence": round(confidence, 4),
        "value": round(peg_ratio, 2),  # Return the PEG ratio
        "details": {
            "peg_ratio": round(peg_ratio, 2),
            "data_source": data_source,
            "raw_peg_provided": peg_ratio_str,  # Include raw value for context
            "raw_pe_provided": pe_ratio_str,
            "threshold_undervalued": peg_settings.THRESHOLD_LOW_PEG,  # Use setting
            "threshold_overvalued": peg_settings.THRESHOLD_HIGH_PEG,  # Use setting
        },
        "agent_name": agent_name,
    }

    return result
