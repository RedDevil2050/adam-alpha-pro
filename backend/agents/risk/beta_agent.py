import pandas as pd
from backend.utils.data_provider import fetch_price_series
from backend.utils.cache_utils import redis_client
from backend.config.settings import settings
from backend.agents.risk.utils import tracker

agent_name = "beta_agent"

async def run(symbol: str) -> dict:
    cache_key = f"{agent_name}:{symbol}"
    # 1) Cache check
    cached = await redis_client.get(cache_key)
    if cached:
        return cached

    # 2) Fetch price series for symbol and market index
    symbol_prices = await fetch_price_series(symbol)
    market_symbol = getattr(settings, 'market_index_symbol', '^NSEI')
    market_prices = await fetch_price_series(market_symbol)

    # 3) Validate data length
    if not symbol_prices or not market_prices or len(symbol_prices) < 2 or len(market_prices) < 2:
        result = {"symbol": symbol, "verdict": "NO_DATA", "confidence": 0.0, "value": None, "details": {}, "agent_name": agent_name}
    else:
        # 4) Compute returns
        sym_ret = pd.Series(symbol_prices).pct_change().dropna()
        mkt_ret = pd.Series(market_prices).pct_change().dropna()
        # Align lengths
        n = min(len(sym_ret), len(mkt_ret))
        sym_ret, mkt_ret = sym_ret.iloc[-n:], mkt_ret.iloc[-n:]

        # 5) Compute beta: cov(sym, mkt)/var(mkt)
        cov = sym_ret.cov(mkt_ret)
        var = mkt_ret.var()
        beta = float(cov / var) if var != 0 else None

        # 6) Normalize & verdict
        if beta is None:
            result = {"symbol": symbol, "verdict": "ERROR", "confidence": 0.0, "value": None, "details": {}, "agent_name": agent_name}
        else:
            # Beta <1 → lower risk, Beta >2 → higher risk
            if beta < 1.0:
                score = 1.0
                verdict = "LOW_RISK"
            elif beta > 2.0:
                score = 0.0
                verdict = "HIGH_RISK"
            else:
                score = float((2.0 - beta) / 1.0)
                verdict = "MODERATE_RISK"

            result = {
                "symbol": symbol,
                "verdict": verdict,
                "confidence": round(score, 4),
                "value": round(beta, 4),
                "details": {"beta": round(beta, 4)},
                "score": score,
                "agent_name": agent_name
            }

    # 7) Cache & track
    await redis_client.set(cache_key, result, ex=3600)
    tracker.update("risk", agent_name, "implemented")
    return result
