from backend.utils.cache_utils import redis_client
from backend.agents.esg.utils import fetch_esg_breakdown, tracker
from backend.agents.decorators import standard_agent_execution

agent_name = "composite_esg_agent"
AGENT_CATEGORY = "esg"  # Define category for the decorator


@standard_agent_execution(
    agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=3600
)
async def run(symbol: str, agent_outputs: dict) -> dict:
    # Decorator handles cache check, so remove manual cache logic

    try:
        # Fetch breakdown or use sub-agent outputs
        breakdown = await fetch_esg_breakdown(symbol)
        # Attempt to use breakdown, fallback to agent_outputs
        env = breakdown.get("environmental") or agent_outputs.get(
            "environmental_agent", {}
        ).get("score")
        soc = breakdown.get("social") or agent_outputs.get("social_agent", {}).get(
            "score"
        )
        gov = breakdown.get("governance") or agent_outputs.get(
            "governance_agent", {}
        ).get("score")

        if None in (env, soc, gov):
            result = {
                "symbol": symbol,
                "verdict": "NO_DATA",
                "confidence": 0.0,
                "value": None,
                "details": {},
                "agent_name": agent_name,
            }
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

            result = {
                "symbol": symbol,
                "verdict": verdict,
                "confidence": composite,
                "value": round(composite * 100, 2),
                "details": {"environmental": env, "social": soc, "governance": gov},
                "score": composite,
                "agent_name": agent_name,
            }

        # Decorator handles caching and tracker update
        return result

    except Exception as e:
        return {
            "symbol": symbol,
            "verdict": "ERROR",
            "confidence": 0.0,
            "value": None,
            "details": {},
            "error": str(e),
            "agent_name": agent_name,
        }
