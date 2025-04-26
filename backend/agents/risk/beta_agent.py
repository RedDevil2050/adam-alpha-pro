import pandas as pd
import numpy as np
from backend.utils.data_provider import fetch_price_series
from backend.utils.cache_utils import redis_client
from backend.config.settings import settings

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
        # Calculate returns
        sym_ret = pd.Series(symbol_prices).pct_change().dropna()
        mkt_ret = pd.Series(market_prices).pct_change().dropna()
        
        # Beta calculation
        beta = float(sym_ret.cov(mkt_ret) / mkt_ret.var())
        
        # Value at Risk (VaR) calculation
        confidence_level = 0.95
        var = float(np.percentile(sym_ret, (1 - confidence_level) * 100))
        
        # Sharpe Ratio
        risk_free = settings.RISK_FREE_RATE or 0.04
        excess_ret = sym_ret - risk_free/252  # Daily adjustment
        sharpe = float(np.sqrt(252) * excess_ret.mean() / excess_ret.std())
        
        # Correlation analysis
        correlation = float(sym_ret.corr(mkt_ret))
        
        # Risk scoring based on multiple metrics
        beta_score = max(0, 1 - abs(beta - 1))
        var_score = max(0, 1 + var/0.05)  # Normalize VaR
        sharpe_score = min(1, max(0, sharpe/3))
        
        composite_score = (beta_score * 0.4 + var_score * 0.3 + sharpe_score * 0.3)
        
        if composite_score > 0.7:
            verdict = "LOW_RISK"
        elif composite_score > 0.4:
            verdict = "MODERATE_RISK" 
        else:
            verdict = "HIGH_RISK"

        result = {
            "symbol": symbol,
            "verdict": verdict,
            "confidence": round(composite_score * 100, 2),
            "value": round(beta, 4),
            "details": {
                "beta": round(beta, 4),
                "value_at_risk": round(var * 100, 2),
                "sharpe_ratio": round(sharpe, 2),
                "market_correlation": round(correlation, 2),
                "risk_scores": {
                    "beta": round(beta_score, 2),
                    "var": round(var_score, 2),
                    "sharpe": round(sharpe_score, 2)
                }
            },
            "score": composite_score,
            "agent_name": agent_name
        }

    # 7) Cache & track
    await redis_client.set(cache_key, result, ex=3600)
    tracker.update("risk", agent_name, "implemented")
    return result
