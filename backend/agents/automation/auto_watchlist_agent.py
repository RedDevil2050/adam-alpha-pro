from backend.utils.data_provider import fetch_price_series
from backend.utils.cache_utils import redis_client
from backend.config.settings import settings
from backend.agents.automation.utils import tracker

agent_name = "auto_watchlist_agent"


async def run(symbol: str, agent_outputs: dict = {}) -> dict:
    cache_key = f"{agent_name}:{symbol}"
    cached = await redis_client.get(cache_key)
    if cached:
        return cached

    # Fetch 30-day price series to check momentum
    prices = await fetch_price_series(symbol, source_preference=["api", "scrape"])

    # Evaluate signals from agent_outputs
    flags = []
    for key, out in agent_outputs.items():
        if out.get("verdict") in ("STRONG_BUY", "BUY", "POSITIVE"):
            flags.append(key)

    # Simple momentum: last price > first
    if prices and prices[-1] > prices[0]:
        flags.append("Positive Momentum")

    verdict = "WATCH" if flags else "IGNORE"
    confidence = min(len(flags) / (len(agent_outputs) + 1), 1.0)

    result = {
        "symbol": symbol,
        "verdict": verdict,
        "confidence": round(confidence, 4),
        "value": len(flags),
        "details": {"signals": flags},
        "score": confidence,
        "agent_name": agent_name,
    }

    await redis_client.set(cache_key, result, ex=settings.agent_cache_ttl)
    tracker.update("automation", agent_name, "implemented")
    return result
