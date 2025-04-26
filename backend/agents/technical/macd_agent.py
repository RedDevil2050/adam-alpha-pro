import pandas as pd
import numpy as np
from backend.utils.data_provider import fetch_ohlcv_series
from backend.utils.cache_utils import redis_client
from backend.agents.technical.utils import tracker
from backend.quant.core import QuantCore
from backend.quant.indicators import TechnicalIndicators

agent_name = "macd_agent"

async def run(symbol: str) -> dict:
    cache_key = f"{agent_name}:{symbol}"
    # 1) Cache check
    cached = await redis_client.get(cache_key)
    if cached:
        return cached

    # 2) Fetch OHLCV (API first, then scraper)
    df = await fetch_ohlcv_series(symbol)
    if df is None or df.empty:
        result = {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {},
            "agent_name": agent_name
        }
    else:
        # Calculate comprehensive indicators
        indicators = TechnicalIndicators.calculate_all(df)
        
        # Get returns for risk analysis
        returns = df['close'].pct_change().dropna()
        risk_metrics = QuantCore.calculate_risk_metrics(returns)
        
        # Enhanced MACD with risk adjustment
        macd_hist = indicators['macd']
        signal_strength = abs(macd_hist[-1]) / macd_hist.std()
        
        # Risk-adjusted score
        risk_score = 1 - abs(risk_metrics['hist_var_95'])
        final_score = signal_strength * risk_score
        
        # Verdict logic with risk consideration
        if final_score > 0.7 and risk_metrics['sharpe'] > 1:
            verdict = "STRONG_BUY"
        elif final_score > 0.5:
            verdict = "BUY"
        elif final_score < 0.3:
            verdict = "AVOID"
        else:
            verdict = "HOLD"

        result = {
            "symbol": symbol,
            "verdict": verdict,
            "confidence": round(final_score * 100, 2),
            "value": round(macd_hist[-1], 4),
            "details": {
                "macd_signal": round(signal_strength, 4),
                "risk_metrics": risk_metrics,
                "technical_indicators": {k: round(float(v[-1]), 4) for k, v in indicators.items()}
            },
            "agent_name": agent_name
        }

    # 6) Cache result for 1 hour
    await redis_client.set(cache_key, result, ex=3600)
    # 7) Track progress
    tracker.update("technical", agent_name, "implemented")

    return result
