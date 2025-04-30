import asyncio
from backend.utils.data_provider import fetch_price_series
from backend.orchestrator import run_full_cycle
from backend.utils.cache_utils import get_redis_client
from backend.config.settings import settings
from backend.agents.automation.utils import tracker

agent_name = "bulk_portfolio_agent"


async def run(symbols: list) -> dict:
    redis_client = await get_redis_client()
    cache_key = f"{agent_name}:{','.join(symbols)}"
    cached = await redis_client.get(cache_key)
    if cached:
        return cached

    # Fetch price series for first symbol to validate dual-channel
    prices = await fetch_price_series(symbols[0], source_preference=["api", "scrape"])

    # Run full cycle for each symbol
    results = {}
    for sym in symbols:
        cycle = await run_full_cycle([sym])
        results[sym] = {
            "verdict": cycle[0].get("verdict"),
            "score": cycle[0].get("score"),
        }

    # Portfolio summary: average score, count of BUYs
    scores = [v["score"] for v in results.values()]
    avg_score = sum(scores) / len(scores) if scores else 0.0
    buy_count = sum(
        1 for v in results.values() if v["verdict"] in ("STRONG_BUY", "BUY")
    )

    result = {
        "symbol": None,
        "verdict": "COMPLETED",
        "confidence": round(avg_score, 4),
        "value": len(symbols),
        "details": {
            "avg_score": avg_score,
            "buy_count": buy_count,
            "per_symbol": results,
        },
        "score": avg_score,
        "agent_name": agent_name,
    }

    await redis_client.set(cache_key, result, ex=settings.agent_cache_ttl)
    tracker.update("automation", agent_name, "implemented")
    return result
