from backend.utils.cache_utils import get_redis_client
from backend.agents.esg.utils import fetch_esg_breakdown, tracker
from backend.agents.decorators import standard_agent_execution

agent_name = "governance_agent"
AGENT_CATEGORY = "esg"  # Define category for the decorator


@standard_agent_execution(
    agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=3600
)
async def run(symbol: str, agent_outputs: dict = None) -> dict:
    # Decorator handles cache check, so remove manual cache logic
    
    # Fetch ESG breakdown
    scores = await fetch_esg_breakdown(symbol)
    value = scores.get("governance")
    if value is None:
        return {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {"reason": "No governance ESG data available"},
            "agent_name": agent_name,
        }
    
    # Normalize 0–100 to 0–1
    score = max(0.0, min(1.0, value / 100.0))
    # Verdict mapping
    if score >= 0.75:
        verdict = "EXCELLENT"
    elif score >= 0.5:
        verdict = "GOOD"
    elif score >= 0.25:
        verdict = "FAIR"
    else:
        verdict = "POOR"
    
    # Decorator handles caching and tracker update
    return {
        "symbol": symbol,
        "verdict": verdict,
        "confidence": score,
        "value": value,
        "details": {"subscore": value},
        "score": score,
        "agent_name": agent_name,
    }
