import asyncio
from backend.utils.cache_utils import get_redis_client
from backend.config.settings import settings
from backend.agents.intelligence.ai_analysis.utils import tracker
from backend.agents.decorators import standard_agent_execution
import importlib
import json # Import json

agent_name = "peer_compare_agent"
AGENT_CATEGORY = "intelligence"  # Define category for the decorator


@standard_agent_execution(
    agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=3600
)
async def run(symbol: str) -> dict:
    # Decorator handles cache check, so remove manual cache logic

    # Fetch PE ratio
    pe_mod = importlib.import_module("backend.agents.valuation.pe_ratio_agent")
    pe_res = await pe_mod.run(symbol)
    pe = pe_res.get("value")
    # Compare to sector average in settings
    sector_avg = settings.sector_pe_averages.get(symbol, None)
    if pe is None or sector_avg is None:
        result = {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {},
            "agent_name": agent_name,
        }
    else:
        diff = pe - sector_avg
        score = max(0.0, min(1.0, (sector_avg - diff) / sector_avg))
        verdict = "UNDERVALUED" if diff < 0 else "OVERVALUED"
        result = {
            "symbol": symbol,
            "verdict": verdict,
            "confidence": round(score, 4),
            "value": round(diff, 4),
            "details": {"pe": pe, "sector_avg": sector_avg},
            "score": score,
            "agent_name": agent_name,
        }

    # Decorator handles caching, so remove manual cache logic
    tracker.update("intelligence", agent_name, "implemented")
    return result
