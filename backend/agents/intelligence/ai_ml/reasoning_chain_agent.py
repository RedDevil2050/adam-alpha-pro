from backend.utils.cache_utils import get_redis_client
from backend.agents.intelligence.ai_analysis.utils import tracker
import json # Import json
from backend.config.settings import settings
from backend.agents.decorators import standard_agent_execution

agent_name = "reasoning_chain_agent"
AGENT_CATEGORY = "intelligence"  # Define category for the decorator


@standard_agent_execution(
    agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=3600
)
async def run(symbol: str, agent_outputs: dict) -> dict:
    # Decorator handles cache check, so remove manual cache logic
    
    # Build chain-of-thought
    entries = [
        f"{k}:{v.get('verdict')}({v.get('confidence')})"
        for k, v in agent_outputs.items()
    ]
    reasoning = " -> ".join(entries)

    result = {
        "symbol": symbol,
        "verdict": "CHAIN",
        "confidence": 1.0,
        "value": reasoning,
        "details": {"chain": entries},
        "score": 1.0,
        "agent_name": agent_name,
    }

    # Decorator handles caching and tracker update
    return result
