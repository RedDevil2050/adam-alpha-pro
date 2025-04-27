import numpy as np
import pandas as pd
from backend.utils.cache_utils import cache_data_provider

@cache_data_provider(ttl=900)  # 15 minutes cache
async def run(symbol: str = "^NSEI", agent_outputs: dict = {}) -> dict:
    try:
        # Fetch data concurrently
        closes_task = fetch_price_series(symbol)
        vix_task = fetch_price_series("^INDIAVIX")
        closes, vix = await asyncio.gather(closes_task, vix_task)
        
        if closes is None or len(closes) < 260:
            return {
                "symbol": symbol,
                "verdict": "NO_DATA",
                "confidence": 0.0,
                "value": None,
                "details": {},
                "error": "≤260 bars",
                "agent_name": agent_name
            }

        # Vectorized operations
        series = pd.Series(closes)
        dma200 = series.rolling(200).mean()
        slope = (dma200.iloc[-1] - dma200.iloc[-21]) / dma200.iloc[-21]
        
        # Use numpy's built-in methods for efficiency
        vix_arr = np.array(vix or [18])
        vix_current = vix_arr[-1]
        vix_pct95 = np.percentile(vix_arr[-min(250, len(vix_arr)):], 95)

        if slope > 0.02 and vix_current < vix_pct95 * 0.8:
            verdict = "BULL"
        elif slope < -0.02 or vix_current > vix_pct95:
            verdict = "PANIC"
        else:
            verdict = "SIDEWAYS"

        return {"symbol": symbol, "verdict": verdict, "confidence": 100.0,
                "value": float(slope), "details": {"vix": vix_current}, "error": None,
                "agent_name": agent_name}
    except Exception as e:
        logger.error(e)
        return {"symbol": symbol, "verdict": "ERROR", "confidence": 0.0,
                "value": None, "details": {}, "error": str(e), "agent_name": agent_name}
