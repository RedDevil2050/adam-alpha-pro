import asyncio
from backend.utils.data_provider import fetch_alpha_vantage # Use fetch_alpha_vantage
from loguru import logger
from backend.agents.decorators import standard_agent_execution # Import decorator

agent_name = "peg_ratio_agent"
AGENT_CATEGORY = "valuation" # Define category for the decorator

@standard_agent_execution(agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=3600)
async def run(symbol: str, agent_outputs: dict = None) -> dict:
    # Boilerplate handled by decorator

    # Fetch overview data which contains PE Ratio and PEG Ratio
    # Note: Alpha Vantage provides PEG directly, but also PE and Analyst Target Price (which might imply growth)
    # We will prioritize the directly provided PEG, but calculate if needed/possible from PE and Growth Estimate
    overview_data = await fetch_alpha_vantage("query", {"function": "OVERVIEW", "symbol": symbol})

    if not overview_data:
        return {
            "symbol": symbol, "verdict": "NO_DATA", "confidence": 0.0, "value": None,
            "details": {"reason": "Could not fetch overview data from Alpha Vantage"},
            "agent_name": agent_name
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
            logger.info(f"[{agent_name}] Using directly provided PEG ratio for {symbol}: {peg_ratio}")
        except (ValueError, TypeError):
            logger.warning(f"[{agent_name}] Could not parse provided PEG ratio for {symbol}: {peg_ratio_str}. Will attempt calculation if possible.")
            peg_ratio = None # Ensure it's None if parsing failed

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
            "reason": "PEG ratio not provided by Alpha Vantage or could not be parsed/calculated."
        }
        return {
            "symbol": symbol, "verdict": "NO_DATA", "confidence": 0.1, "value": None,
            "details": details,
            "agent_name": agent_name
        }

    # 4. Determine Verdict based on PEG ratio
    # PEG < 1 is often considered potentially undervalued
    # PEG > 2 is often considered potentially overvalued
    if peg_ratio <= 0:
        # Negative PEG usually means negative earnings (negative PE) or zero/negative growth
        verdict = "NEGATIVE_OR_ZERO_PEG"
        confidence = 0.6 # Confidence that the value is problematic or indicates negative earnings/growth
    elif peg_ratio < 1.0:
        verdict = "POTENTIALLY_UNDERVALUED"
        confidence = 0.7
    elif peg_ratio <= 2.0:
        verdict = "FAIRLY_VALUED"
        confidence = 0.5
    else: # peg_ratio > 2.0
        verdict = "POTENTIALLY_OVERVALUED"
        confidence = 0.4

    # Create success result dictionary
    result = {
        "symbol": symbol,
        "verdict": verdict,
        "confidence": round(confidence, 4),
        "value": round(peg_ratio, 2), # Return the PEG ratio
        "details": {
            "peg_ratio": round(peg_ratio, 2),
            "data_source": data_source,
            "raw_peg_provided": peg_ratio_str, # Include raw value for context
            "raw_pe_provided": pe_ratio_str
        },
        "agent_name": agent_name
    }

    return result
