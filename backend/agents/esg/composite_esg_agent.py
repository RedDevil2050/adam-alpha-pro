from backend.utils.cache_utils import redis_client
from backend.agents.esg.utils import fetch_esg_breakdown, tracker

agent_name = "composite_esg_agent"

async def run(symbol: str, agent_outputs: dict) -> dict:
    cache_key = f"{agent_name}:{{symbol}}"
    cached = await redis_client.get(cache_key)
    if cached:
        return cached

    # Fetch breakdown or use sub-agent outputs
    breakdown = await fetch_esg_breakdown(symbol)
    # Attempt to use breakdown, fallback to agent_outputs
    env = breakdown.get('environmental') or agent_outputs.get('environmental_agent', {{}}).get('score')
    soc = breakdown.get('social') or agent_outputs.get('social_agent', {{}}).get('score')
    gov = breakdown.get('governance') or agent_outputs.get('governance_agent', {{}}).get('score')

    if None in (env, soc, gov):
        result = {{"symbol": symbol, "verdict": "NO_DATA", "confidence": 0.0, "value": None, "details": {{}}, "agent_name": agent_name}}
    else:
        composite = (env + soc + gov) / 3.0
        # Verdict mapping
        if composite >= 0.75:
            verdict = "EXCELLENT"
        elif composite >= 0.5:
            verdict = "GOOD"
        elif composite >= 0.25:
            verdict = "FAIR"
        else:
            verdict = "POOR"
        result = {{
            "symbol": symbol,
            "verdict": verdict,
            "confidence": composite,
            "value": round(composite * 100, 2),
            "details": {{"environmental": env, "social": soc, "governance": gov}},
            "score": composite,
            "agent_name": agent_name
        }}

    await redis_client.set(cache_key, result, ex=3600)
    tracker.update("esg", agent_name, "implemented")
    return result
