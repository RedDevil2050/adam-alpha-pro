from backend.utils.data_provider import fetch_eps, fetch_pe_target
from loguru import logger
from backend.agents.decorators import standard_agent_execution # Import decorator

agent_name = "valuation_price_target_agent" # Renamed from price_target_agent
AGENT_CATEGORY = "valuation"

# Apply the decorator
@standard_agent_execution(agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=3600)
async def run(symbol: str, agent_outputs: dict = {}) -> dict:
    eps = await fetch_eps(symbol)
    target_pe = await fetch_pe_target(symbol)

    if not eps or not target_pe:
        # Return NO_DATA format
        return {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {"eps": eps, "target_pe": target_pe},
        }

    target_price = eps * target_pe

    # Return success result
    return {
        "symbol": symbol,
        "verdict": "TARGET_ESTIMATED",
        "confidence": 1.0, # Confidence should be 0.0 to 1.0
        "value": round(target_price, 2),
        "details": {"eps": eps, "target_pe": target_pe},
    }
