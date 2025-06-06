import pkgutil
import importlib
from backend.utils.data_provider import fetch_price_series
from backend.agents.intelligence.utils import tracker
from backend.agents.decorators import standard_agent_execution

agent_name = "composite_valuation_agent"
AGENT_CATEGORY = "intelligence"  # Define category for the decorator


@standard_agent_execution(
    agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=3600
)
async def run(symbol: str) -> dict:
    # Decorator handles cache check, so remove manual cache logic
    
    # Dummy fetch to ensure data load
    _ = await fetch_price_series(symbol, source_preference=["api", "scrape"])

    scores = []
    pkg = importlib.import_module("backend.agents.valuation")
    for _, fullname, _ in pkgutil.walk_packages(
        path=pkg.__path__, prefix="backend.agents.valuation."
    ):
        if fullname.endswith(("utils", "__init__", "base")):
            continue
        mod = importlib.import_module(fullname)
        res = await mod.run(symbol)
        scores.append(res.get("score", 0.0))

    avg = sum(scores) / len(scores) if scores else 0.0
    verdict = (
        "STRONG_BUY"
        if avg >= 0.7
        else "BUY" if avg >= 0.5 else "HOLD" if avg >= 0.3 else "AVOID"
    )

    result = {
        "symbol": symbol,
        "verdict": verdict,
        "confidence": round(avg, 4),
        "value": avg,
        "details": {"scores": scores},
        "score": avg,
        "agent_name": agent_name,
    }

    # Decorator handles caching and tracker update
    return result
