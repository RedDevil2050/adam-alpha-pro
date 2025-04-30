import pandas as pd
from backend.utils.cache_utils import get_redis_client
from backend.utils.data_provider import fetch_eps_data
from backend.agents.forecast.utils import tracker

agent_name = "earnings_forecast_agent"


async def run(symbol: str) -> dict:
    redis_client = await get_redis_client()
    cache_key = f"{agent_name}:{symbol}"
    cached = await redis_client.get(cache_key)
    if cached:
        return cached

    # Fetch EPS history
    eps_ts = await fetch_eps_data(symbol)
    if not eps_ts or len(eps_ts) < 2:
        result = {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {},
            "score": 0.0,
            "agent_name": agent_name,
        }
    else:
        # Compute EPS trend: last minus first over periods
        eps_series = pd.Series(eps_ts)
        trend = float(eps_series.iloc[-1] - eps_series.iloc[0])
        if trend > 0:
            verdict = "UPTREND"
            # Normalize confidence by relative change
            score = (
                min(trend / eps_series.iloc[0], 1.0) if eps_series.iloc[0] != 0 else 1.0
            )
        else:
            verdict = "DOWNTREND"
            score = (
                min(abs(trend) / eps_series.iloc[0], 1.0)
                if eps_series.iloc[0] != 0
                else 1.0
            )

        result = {
            "symbol": symbol,
            "verdict": verdict,
            "confidence": round(score, 4),
            "value": trend,
            "details": {"eps_trend": trend},
            "score": score,
            "agent_name": agent_name,
        }

    await redis_client.set(cache_key, result, ex=None)
    tracker.update("forecast", agent_name, "implemented")
    return result
