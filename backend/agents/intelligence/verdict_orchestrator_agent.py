from backend.utils.cache_utils import redis_client
from backend.agents.intelligence.utils import tracker

agent_name = "verdict_orchestrator_agent"

async def run(symbol: str, agent_outputs: dict = {}) -> dict:
    cache_key = f"{agent_name}:{symbol}"
    cached = await redis_client.get(cache_key)
    if cached:
        return cached

    try:
        # Aggregate scores and verdicts from agent outputs
        scores = [v.get("score", 0.0) for v in agent_outputs.values()]
        avg_score = sum(scores) / len(scores) if scores else 0.0

        # Determine overall verdict
        if avg_score >= 0.7:
            verdict = "STRONG_BUY"
        elif avg_score >= 0.5:
            verdict = "BUY"
        elif avg_score >= 0.3:
            verdict = "HOLD"
        else:
            verdict = "SELL"

        result = {
            "symbol": symbol,
            "verdict": verdict,
            "confidence": round(avg_score, 4),
            "value": avg_score,
            "details": {"agent_scores": agent_outputs},
            "agent_name": agent_name
        }

        await redis_client.set(cache_key, result, ex=3600)
        tracker.update("intelligence", agent_name, "implemented")
        return result

    except Exception as e:
        return {
            "symbol": symbol,
            "verdict": "ERROR",
            "confidence": 0.0,
            "value": None,
            "details": {},
            "error": str(e),
            "agent_name": agent_name
        }
