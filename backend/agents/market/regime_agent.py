
import numpy as np, pandas as pd
from backend.utils.data_provider import fetch_price_series
from backend.utils.cache_utils import cache_data_provider
from loguru import logger

agent_name = "regime_agent"

@cache_data_provider(ttl=900)
async def run(symbol: str = "^NSEI", agent_outputs: dict = {}) -> dict:
    try:
        closes = await fetch_price_series(symbol)
        if closes is None or len(closes) < 260:
            return {"symbol": symbol, "verdict": "NO_DATA", "confidence": 0.0,
                    "value": None, "details": {}, "error": "≤260 bars", "agent_name": agent_name}

        series = pd.Series(closes)
        dma200 = series.rolling(200).mean()
        slope = (dma200.iloc[-1] - dma200.iloc[-21]) / dma200.iloc[-21]
        vix = await fetch_price_series("^INDIAVIX") or [18]
        vix_pct95 = np.percentile(vix[-250:], 95)

        if slope > 0.02 and vix[-1] < vix_pct95 * 0.8:
            verdict = "BULL"
        elif slope < -0.02 or vix[-1] > vix_pct95:
            verdict = "PANIC"
        else:
            verdict = "SIDEWAYS"

        return {"symbol": symbol, "verdict": verdict, "confidence": 100.0,
                "value": float(slope), "details": {"vix": vix[-1]}, "error": None,
                "agent_name": agent_name}
    except Exception as e:
        logger.error(e)
        return {"symbol": symbol, "verdict": "ERROR", "confidence": 0.0,
                "value": None, "details": {}, "error": str(e), "agent_name": agent_name}
