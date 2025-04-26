import importlib
from backend.utils.cache_utils import redis_client
from backend.utils.data_provider import fetch_price_series
from backend.agents.intelligence.utils import tracker

agent_name = "factor_score_agent"

async def run(symbol: str) -> dict:
    cache_key = f"{agent_name}:{symbol}"
    cached = await redis_client.get(cache_key)
    if cached:
        return cached

    # Ensure data load
    _ = await fetch_price_series(symbol, source_preference=["api","scrape"])

    scores = []
    try:
        rsi = await importlib.import_module("backend.agents.technical.rsi_agent").run(symbol)
        pe = await importlib.import_module("backend.agents.valuation.pe_ratio_agent").run(symbol)
        scores = [rsi.get("score", 0.0), pe.get("score", 0.0)]
    except:
        scores = []

    avg = sum(scores) / len(scores) if scores else 0.0
    verdict = "BUY" if avg >= 0.5 else "AVOID"
    result = {
        "symbol": symbol,
        "verdict": verdict,
        "confidence": round(avg, 4),
        "value": avg,
        "details": {"factor_scores": scores},
        "score": avg,
        "agent_name": agent_name
    }

    await redis_client.set(cache_key, result, ex=None)
    tracker.update("intelligence", agent_name, "implemented")
    return result
