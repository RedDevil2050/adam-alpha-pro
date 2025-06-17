import pandas as pd
from backend.utils.data_provider import fetch_ohlcv_series
from backend.utils.cache_utils import get_redis_client
from backend.agents.analysis.technical.utils import tracker
from datetime import datetime, timedelta
from backend.agents.decorators import standard_agent_execution

agent_name = "bollinger_agent"
AGENT_CATEGORY = "technical"  # Define category for the decorator


@standard_agent_execution(
    agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=3600
)
async def run(symbol: str, agent_outputs: dict = None, window: int = 20, num_std: float = 2.0) -> dict:
    # Decorator handles cache check, so remove manual cache logic
    
    # Fetch OHLCV data
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    df = await fetch_ohlcv_series(symbol, start_date, end_date)
    if df is None or df.empty or len(df) < window:
        result = {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {},
            "agent_name": agent_name,
        }
    else:
        close = df["close"]
        # Compute moving average and standard deviation
        ma = close.rolling(window=window, min_periods=window).mean()
        std = close.rolling(window=window, min_periods=window).std()

        last_ma = ma.iloc[-1]
        last_std = std.iloc[-1]
        last_close = close.iloc[-1]

        upper_band = last_ma + num_std * last_std
        lower_band = last_ma - num_std * last_std

        # Normalize and map verdict
        if last_close < lower_band:
            score = 1.0
            verdict = "BUY"
        elif last_close > upper_band:
            score = 0.0
            verdict = "AVOID"
        else:
            # Position between bands: invert relative position
            score = float((upper_band - last_close) / (upper_band - lower_band))
            verdict = "HOLD"

        result = {
            "symbol": symbol,
            "verdict": verdict,
            "confidence": score,
            "value": round(last_close, 4),
            "details": {
                "upper_band": round(upper_band, 4),
                "lower_band": round(lower_band, 4),
                "moving_average": round(last_ma, 4),
                "std_dev": round(last_std, 4),
            },
            "score": score,
            "agent_name": agent_name,
        }

    # Decorator handles caching and tracker update
    return result
