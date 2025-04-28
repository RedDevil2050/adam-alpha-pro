from backend.utils.data_provider import fetch_alpha_vantage # Use fetch_alpha_vantage
from loguru import logger
from backend.agents.decorators import standard_agent_execution # Import decorator
# TODO: Import get_settings and add EvEbitdaAgentSettings to settings.py
# from backend.config.settings import get_settings

agent_name = "ev_ebitda_agent"
AGENT_CATEGORY = "valuation" # Define category for the decorator

@standard_agent_execution(agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=3600)
async def run(symbol: str, agent_outputs: dict = None) -> dict:
    \"\"\"
    Calculates the Enterprise Value to EBITDA (EV/EBITDA) ratio for a given stock symbol and assesses its valuation.

    Purpose:
        Determines the EV/EBITDA ratio, which compares the total value of a company (enterprise value)
        to its earnings before interest, taxes, depreciation, and amortization (EBITDA).
        It's often used as an alternative to P/E, especially for companies with significant debt or depreciation.
        Lower ratios generally suggest potential undervaluation.

    Metrics Calculated:
        - EV/EBITDA Ratio (Enterprise Value / EBITDA)

    Logic:
        1. Fetches company overview data from Alpha Vantage, which includes the EV/EBITDA ratio.
        2. Parses the EV/EBITDA ratio value. Handles cases where data is missing, 'None', or non-numeric.
        3. Compares the EV/EBITDA ratio against configurable thresholds (THRESHOLD_LOW_EV_EBITDA, THRESHOLD_HIGH_EV_EBITDA):
            - If EV/EBITDA <= 0: Verdict is 'NEGATIVE_OR_ZERO' (indicates negative EBITDA or other issues).
            - If 0 < EV/EBITDA < THRESHOLD_LOW_EV_EBITDA: Verdict is 'UNDERVALUED'.
            - If THRESHOLD_LOW_EV_EBITDA <= EV/EBITDA < THRESHOLD_HIGH_EV_EBITDA: Verdict is 'FAIRLY_VALUED'.
            - If EV/EBITDA >= THRESHOLD_HIGH_EV_EBITDA: Verdict is 'OVERVALUED'.
        4. Sets a fixed confidence score based on the verdict category.

    Dependencies:
        - Requires company overview data containing the EV/EBITDA ratio (e.g., from Alpha Vantage).

    Configuration Used (Requires manual addition to settings.py):
        - `settings.agent_settings.ev_ebitda.THRESHOLD_LOW_EV_EBITDA`: Upper bound for 'UNDERVALUED'.
        - `settings.agent_settings.ev_ebitda.THRESHOLD_HIGH_EV_EBITDA`: Upper bound for 'FAIRLY VALUED'.

    Return Structure:
        A dictionary containing:
        - symbol (str): The stock symbol.
        - verdict (str): 'UNDERVALUED', 'FAIRLY_VALUED', 'OVERVALUED', 'NEGATIVE_OR_ZERO', 'NO_DATA', or 'INVALID_DATA'.
        - confidence (float): A fixed score based on the verdict category (0.0 to 1.0).
        - value (float | None): The calculated/provided EV/EBITDA ratio, or None if not available/applicable.
        - details (dict): Contains the raw EV/EBITDA ratio, data source, and configured thresholds.
        - agent_name (str): The name of this agent.
        - error (str | None): Error message if an issue occurred (handled by decorator).
    \"\"\"
    # Boilerplate handled by decorator
    # TODO: Fetch settings
    # settings = get_settings()
    # ev_settings = settings.agent_settings.ev_ebitda
    # Define thresholds directly for now, replace with settings later
    THRESHOLD_LOW_EV_EBITDA = 10.0
    THRESHOLD_HIGH_EV_EBITDA = 15.0

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
    # Determine verdict based on standardized thresholds
    if ev_ebitda <= 0:
        # Negative or zero EV/EBITDA often indicates issues (e.g., negative EBITDA)
        verdict = "NEGATIVE_OR_ZERO" # Specific case
        confidence = 0.7 # Confidence that the value is problematic
    elif ev_ebitda < THRESHOLD_LOW_EV_EBITDA: # Use threshold
        verdict = "UNDERVALUED" # Standardized verdict
        confidence = 0.8 # High confidence for low EV/EBITDA
    elif ev_ebitda < THRESHOLD_HIGH_EV_EBITDA: # Use threshold
        verdict = "FAIRLY_VALUED" # Standardized verdict
        confidence = 0.6
    else: # EV/EBITDA >= THRESHOLD_HIGH_EV_EBITDA
        verdict = "OVERVALUED" # Standardized verdict
        confidence = 0.4

    # Create success result dictionary
    result = {
        "symbol": symbol,
        "verdict": verdict,
        "confidence": round(confidence, 4),
        "value": round(ev_ebitda, 2), # Return the EV/EBITDA ratio
        "details": {
            "ev_ebitda": round(ev_ebitda, 2),
            "data_source": "alpha_vantage_overview",
            # TODO: Add thresholds from settings to details
            "threshold_undervalued": THRESHOLD_LOW_EV_EBITDA, # Using placeholder value for now
            "threshold_overvalued": THRESHOLD_HIGH_EV_EBITDA  # Using placeholder value for now
        },
        "agent_name": agent_name
    }

    return result
