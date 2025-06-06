from backend.utils.cache_utils import get_redis_client
from backend.agents.intelligence.utils import tracker
import json # Import json
from backend.config.settings import settings
from backend.agents.decorators import standard_agent_execution

agent_name = "smart_explanation_agent"
AGENT_CATEGORY = "intelligence"  # Define category for the decorator


@standard_agent_execution(
    agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=3600
)
async def run(symbol: str, agent_outputs: dict) -> dict:
    # Decorator handles cache check, so remove manual cache logic
    
    # Summarize top signals
    top = sorted(
        agent_outputs.items(), key=lambda x: x[1].get("confidence", 0), reverse=True
    )[:3]
    explanation = "; ".join([f"{k}→{v.get('verdict')}" for k, v in top])

    result = {
        "symbol": symbol,
        "verdict": "EXPLANATION",
        "confidence": 1.0,
        "value": explanation,
        "details": {"explanation": explanation},
        "score": 1.0,
        "agent_name": agent_name,
    }

    # Decorator handles caching and tracker update
    return result
