from backend.utils.data_provider import fetch_alpha_vantage # Use fetch_alpha_vantage
from loguru import logger
from backend.agents.decorators import standard_agent_execution # Import decorator

agent_name = "ev_ebitda_agent"
AGENT_CATEGORY = "valuation" # Define category for the decorator

@standard_agent_execution(agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=3600)
async def run(symbol: str, agent_outputs: dict = None) -> dict:
    # Boilerplate handled by decorator

    # Fetch overview data which contains EV/EBITDA
    overview_data = await fetch_alpha_vantage("query", {"function": "OVERVIEW", "symbol": symbol})

    if not overview_data:
        return {
            "symbol": symbol, "verdict": "NO_DATA", "confidence": 0.0, "value": None,
            "details": {"reason": "Could not fetch overview data from Alpha Vantage"},
            "agent_name": agent_name
        }

    ev_ebitda_str = overview_data.get("EVToEBITDA")
    ev_ebitda = None

    if ev_ebitda_str and ev_ebitda_str.lower() not in ["none", "-", ""]:
        try:
            ev_ebitda = float(ev_ebitda_str)
        except (ValueError, TypeError):
            logger.warning(f"[{agent_name}] Could not parse EV/EBITDA for {symbol}: {ev_ebitda_str}")
            return {
                "symbol": symbol, "verdict": "INVALID_DATA", "confidence": 0.1, "value": None,
                "details": {"raw_ev_ebitda": ev_ebitda_str, "reason": "Could not parse EV/EBITDA value"},
                "agent_name": agent_name
            }
    else:
        # Handle cases where EV/EBITDA is explicitly None or missing
        logger.warning(f"[{agent_name}] EV/EBITDA not available for {symbol} in overview data.")
        return {
            "symbol": symbol, "verdict": "NO_DATA", "confidence": 0.5, "value": None, # Confidence 0.5 as we know it's missing
            "details": {"raw_ev_ebitda": ev_ebitda_str, "reason": "EV/EBITDA value not provided or is None"},
            "agent_name": agent_name
        }

    # EV/EBITDA is successfully parsed
    # Determine verdict based on common thresholds (lower is generally better)
    # These thresholds can be sector-dependent in a more advanced version
    if ev_ebitda <= 0:
        # Negative or zero EV/EBITDA often indicates issues (e.g., negative EBITDA)
        verdict = "NEGATIVE_OR_ZERO"
        confidence = 0.7 # Confidence that the value is problematic
    elif ev_ebitda < 10:
        verdict = "POTENTIALLY_UNDERVALUED"
        confidence = 0.8
    elif ev_ebitda < 15: # Adjusted threshold
        verdict = "FAIRLY_VALUED"
        confidence = 0.6
    else: # EV/EBITDA >= 15
        verdict = "POTENTIALLY_OVERVALUED"
        confidence = 0.4

    # Create success result dictionary
    result = {
        "symbol": symbol,
        "verdict": verdict,
        "confidence": round(confidence, 4),
        "value": round(ev_ebitda, 2), # Return the EV/EBITDA ratio
        "details": {
            "ev_ebitda": round(ev_ebitda, 2),
            "data_source": "alpha_vantage_overview"
        },
        "agent_name": agent_name
    }

    return result
