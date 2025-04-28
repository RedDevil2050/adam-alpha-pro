import asyncio
from backend.utils.data_provider import fetch_alpha_vantage # Use fetch_alpha_vantage
from loguru import logger
from backend.agents.decorators import standard_agent_execution # Import decorator

agent_name = "pe_ratio_agent"
AGENT_CATEGORY = "valuation" # Define category for the decorator

@standard_agent_execution(agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=3600)
async def run(symbol: str, agent_outputs: dict = None) -> dict:
    # Boilerplate handled by decorator

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
    # Determine verdict based on common thresholds (these are general and can vary by industry/market)
    if pe_ratio <= 0:
        # Negative or zero PE usually means negative earnings
        verdict = "NEGATIVE_EARNINGS"
        confidence = 0.7 # Confidence that the value indicates negative earnings
    elif pe_ratio < 15:
        verdict = "LOW_PE" # Potentially undervalued
        confidence = 0.6
    elif pe_ratio < 25:
        verdict = "MODERATE_PE" # Often considered reasonable range
        confidence = 0.5
    else: # PE >= 25
        verdict = "HIGH_PE" # Potentially overvalued, common for growth stocks
        confidence = 0.4

    # Create success result dictionary
    result = {
        "symbol": symbol,
        "verdict": verdict,
        "confidence": round(confidence, 4),
        "value": round(pe_ratio, 2), # Return the PE ratio
        "details": {
            "pe_ratio": round(pe_ratio, 2),
            "data_source": "alpha_vantage_overview"
        },
        "agent_name": agent_name
    }

    return result
