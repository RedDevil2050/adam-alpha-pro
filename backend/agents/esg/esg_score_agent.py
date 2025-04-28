from backend.utils.data_provider import fetch_esg_data
from backend.agents.decorators import standard_agent_execution # Import decorator
from backend.config.settings import get_settings # Added import

agent_name = "esg_score_agent" # Define agent name
AGENT_CATEGORY = "esg" # Define category for the decorator

@standard_agent_execution(agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=86400) # Apply decorator
async def run(symbol: str, agent_outputs: dict = None) -> dict: # Define run function
    # Boilerplate (cache check, try/except, cache set, tracker, error handling) is handled by decorator

    # Fetch settings
    settings = get_settings()
    esg_settings = settings.agent_settings.esg_score

    # Fetch ESG data for the given symbol (Core Logic)
    esg_data = await fetch_esg_data(symbol)

    if not esg_data:
        # Return NO_DATA format (decorator won't cache this)
        return {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {"reason": "No ESG data available"},
            "error": None, # Explicitly None for NO_DATA
            "agent_name": agent_name # Decorator might overwrite this
        }

    # Calculate ESG score (Core Logic)
    environmental = esg_data.get("environmental", 0)
    social = esg_data.get("social", 0)
    governance = esg_data.get("governance", 0)

    # Basic scoring, adjust as needed
    # Assuming scores are out of 100, normalize if necessary
    esg_score = (environmental + social + governance) / 3

    # Determine verdict based on score (using settings)
    if esg_score > esg_settings.THRESHOLD_STRONG_ESG: # Use setting
        verdict = "STRONG_ESG"
    elif esg_score > esg_settings.THRESHOLD_MODERATE_ESG: # Use setting
        verdict = "MODERATE_ESG"
    else:
        verdict = "WEAK_ESG"

    # Create success result dictionary (Core Logic)
    result = {
        "symbol": symbol,
        "verdict": verdict,
        "confidence": round(esg_score, 2), # Use score as confidence, or derive differently
        "value": round(esg_score, 2),
        "details": {
            "environmental_score": environmental,
            "social_score": social,
            "governance_score": governance,
            "composite_esg_score": round(esg_score, 2),
            "threshold_strong": esg_settings.THRESHOLD_STRONG_ESG, # Added threshold
            "threshold_moderate": esg_settings.THRESHOLD_MODERATE_ESG, # Added threshold
        },
        "error": None, # Explicitly None for success
        "agent_name": agent_name # Decorator might overwrite this
    }
    return result