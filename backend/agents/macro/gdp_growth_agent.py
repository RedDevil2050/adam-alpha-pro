
from backend.utils.cache_utils import redis_client
from backend.utils.data_provider import fetch_gdp_growth
from backend.agents.macro.utils import tracker

agent_name = "gdp_growth_agent"

async def run(symbol: str, country: str = "IND") -> dict:
    cache_key = f"{agent_name}:{country}"
    cached = await redis_client.get(cache_key)
    if cached:
        return cached

    value = await fetch_gdp_growth(country)
    if value is None:
        result = {"symbol": country, "verdict":"NO_DATA","confidence":0.0,"value":None,
                  "details":{},"agent_name":agent_name}
    else:
        if value >= 5:
            verdict, score = "EXPANSION", 1.0
        elif value <= 0:
            verdict, score = "RECESSION", 0.0
        else:
            score = (value - 0) / 5.0
            verdict = "MODERATE"
        result = {"symbol": country,"verdict":verdict,"confidence":round(score,4),
                  "value":round(value,2),"details":{"gdp_growth_pct":value},
                  "score":score,"agent_name":agent_name}

    await redis_client.set(cache_key, result, ex=86400)
    tracker.update("macro", agent_name, "implemented")
    return result
