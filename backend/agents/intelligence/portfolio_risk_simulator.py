import numpy as np
import pandas as pd
from backend.utils.cache_utils import redis_client
from backend.utils.data_provider import fetch_price_series
from backend.agents.intelligence.utils import tracker

agent_name = "portfolio_risk_simulator"

async def run(symbols: list, weights: list = None) -> dict:
    cache_key = f"{agent_name}:{','.join(symbols)}"
    cached = await redis_client.get(cache_key)
    if cached:
        return cached

    # 1) Fetch price series for each symbol
    data = {sym: await fetch_price_series(sym, source_preference=["api","scrape"]) for sym in symbols}
    prices_df = pd.DataFrame(data)
    # 2) Compute log returns
    returns = np.log(prices_df / prices_df.shift(1)).dropna()
    # 3) Default equal weights
    if weights is None:
        weights = [1/len(symbols)] * len(symbols)
    # 4) Portfolio returns
    port_r = returns.dot(weights)
    var95 = np.percentile(port_r, 5)
    cvar95 = port_r[port_r <= var95].mean()
    # 5) Normalize
    score = min(abs(cvar95) / abs(var95) if var95!=0 else 0, 1.0)
    # Verdict
    if score < 0.02:
        verdict = "LOW_RISK"
    elif score < 0.05:
        verdict = "MEDIUM_RISK"
    else:
        verdict = "HIGH_RISK"

    result = {
        "symbol": ",".join(symbols),
        "verdict": verdict,
        "confidence": round(score,4),
        "value": {"VaR95": round(var95,4), "CVaR95": round(cvar95,4)},
        "details": {},
        "score": score,
        "agent_name": agent_name
    }

    await redis_client.set(cache_key, result, ex=None)
    tracker.update("intelligence", agent_name, "implemented")
    return result
