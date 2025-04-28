import asyncio
from backend.utils.data_provider import fetch_alpha_vantage # Use fetch_alpha_vantage
from loguru import logger
from backend.agents.decorators import standard_agent_execution # Import decorator

agent_name = "pb_ratio_agent"
AGENT_CATEGORY = "valuation" # Define category for the decorator

@standard_agent_execution(agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=3600)
async def run(symbol: str, agent_outputs: dict = None) -> dict:
    # Boilerplate handled by decorator

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
    # Determine verdict based on common thresholds (lower is generally better, but context matters)
    # P/B < 1 can be good value or distress signal. P/B > 3 often considered high.
    if pb_ratio <= 0:
        # Negative or zero P/B is unusual and likely indicates negative book value (equity)
        verdict = "NEGATIVE_OR_ZERO_BV"
        confidence = 0.7 # Confidence that the value is problematic
    elif pb_ratio < 1.0:
        verdict = "LOW_PB" # Potentially undervalued, or financial/distressed company
        confidence = 0.6 # Moderate confidence, needs context
    elif pb_ratio < 3.0:
        verdict = "MODERATE_PB" # Often considered reasonable range
        confidence = 0.5
    else: # P/B >= 3.0
        verdict = "HIGH_PB" # Potentially overvalued, common for growth stocks
        confidence = 0.4

    # Create success result dictionary
    result = {
        "symbol": symbol,
        "verdict": verdict,
        "confidence": round(confidence, 4),
        "value": round(pb_ratio, 2), # Return the P/B ratio
        "details": {
            "pb_ratio": round(pb_ratio, 2),
            "data_source": "alpha_vantage_overview"
        },
        "agent_name": agent_name
    }

    return result
