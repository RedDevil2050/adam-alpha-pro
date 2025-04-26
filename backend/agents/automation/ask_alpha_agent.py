import asyncio, pkgutil, importlib
from backend.utils.cache_utils import redis_client
from backend.config.settings import settings
from backend.agents.automation.utils import tracker

agent_name = "ask_alpha_agent"

async def run(symbol: str, agent_outputs: dict = {}, question: str = "") -> dict:
    cache_key = f"{agent_name}:{symbol}:{question}"
    cached = await redis_client.get(cache_key)
    if cached:
        return cached

    answer = ""
    q = question.lower()
    # Route based on keywords
    if "price" in q:
        from backend.utils.data_provider import fetch_price_series
        prices = await fetch_price_series(symbol, source_preference=["api","scrape"])
        answer = f"Latest price for {symbol} is {prices[-1]:.2f}"
    elif "eps" in q:
        from backend.utils.data_provider import fetch_eps_data
        eps_ts = await fetch_eps_data(symbol)
        answer = f"Latest EPS for {symbol} is {eps_ts[-1]:.2f}" if eps_ts else "EPS data unavailable"
    elif "verdict" in q or "recommend" in q:
        from backend.brain import aggregate_scores, make_verdict
        # synthesize inputs
        category_results = agent_outputs.get("category_results", {})
        score = aggregate_scores(category_results)
        verdict = make_verdict(score)
        answer = f"Brain recommendation for {symbol}: {verdict}"
    else:
        answer = f"No specialized answer, try asking about price, EPS, or recommendation."

    result = {
        "symbol": symbol,
        "verdict": "INFO",
        "confidence": 1.0,
        "value": answer,
        "details": {"answer": answer},
        "score": 1.0,
        "agent_name": agent_name
    }

    await redis_client.set(cache_key, result, ex=settings.agent_cache_ttl)
    tracker.update("automation", agent_name, "implemented")
    return result
