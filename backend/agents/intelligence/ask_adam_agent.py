from backend.utils.cache_utils import get_redis_client
from backend.utils.data_provider import fetch_price_series, fetch_eps_data
import json # Import json
from backend.agents.intelligence.utils import tracker
from backend.agents.decorators import standard_agent_execution

agent_name = "ask_adam_agent"
AGENT_CATEGORY = "intelligence"  # Define category for the decorator


@standard_agent_execution(
    agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=3600
)
async def run(symbol: str, question: str = "") -> dict:
    # Decorator handles cache check, so remove manual cache logic
    
    q = question.lower()
    if "price" in q:
        prices = await fetch_price_series(symbol, source_preference=["api", "scrape"])
        value = prices[-1] if prices else None
        answer = f"Latest price: {value}"
    elif "eps" in q:
        eps_ts = await fetch_eps_data(symbol)
        value = eps_ts[-1] if eps_ts else None
        answer = f"Latest EPS: {value}"
    else:
        answer = "I can provide price or EPS insights. Try asking specifically."

    result = {
        "symbol": symbol,
        "verdict": "INFO",
        "confidence": 1.0,
        "value": answer,
        "details": {"answer": answer},
        "score": 1.0,
        "agent_name": agent_name,
    }

    # Decorator handles caching and tracker update
    return result
