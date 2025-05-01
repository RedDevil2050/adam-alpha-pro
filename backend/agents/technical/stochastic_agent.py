import pandas as pd
from backend.utils.data_provider import fetch_ohlcv_series
from backend.utils.cache_utils import get_redis_client
from backend.agents.technical.utils import tracker
from backend.config.settings import settings
import datetime
from dateutil.relativedelta import relativedelta

agent_name = "stochastic_agent"


async def run(symbol: str, agent_outputs: dict = None) -> dict:
    cache_key = f"{agent_name}:{symbol}"
    redis_client = await get_redis_client()
    # Cache check
    cached = await redis_client.get(cache_key)
    if cached:
        return cached

    # Define date range (e.g., 7 months for daily data)
    end_date = datetime.date.today()
    start_date = end_date - relativedelta(months=7)

    # Fetch OHLCV series with fallback
    df = await fetch_ohlcv_series(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        interval='1d' # Assuming daily interval is needed
    )
    if df is None or df.empty:
        result = {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {},
            "agent_name": agent_name,
        }
    else:
        k_window = getattr(settings, 'STOCHASTIC_K_WINDOW', 14) # Default 14
        d_window = getattr(settings, 'STOCHASTIC_D_WINDOW', 3)   # Default 3
        oversold_level = getattr(settings, 'STOCHASTIC_OVERSOLD', 20) # Default 20
        overbought_level = getattr(settings, 'STOCHASTIC_OVERBOUGHT', 80) # Default 80

        low_min = df["low"].rolling(k_window).min()
        high_max = df["high"].rolling(k_window).max()
        # Avoid division by zero
        high_low_diff = high_max - low_min
        k = 100 * ((df["close"] - low_min) / high_low_diff.replace(0, np.nan)) # Replace 0 diff with NaN
        k = k.fillna(50) # Fill potential NaNs if high_low_diff was 0

        d = k.rolling(d_window).mean()
        latest_k = float(k.iloc[-1])
        latest_d = float(d.iloc[-1])

        # Verdict mapping using fallback settings
        if latest_k <= oversold_level:
            verdict = "BUY"
            score = 1.0
        elif latest_k >= overbought_level:
            verdict = "AVOID"
            score = 0.0
        else:
            verdict = "HOLD"
            # linear score: buffer between oversold/overbought
            range_span = overbought_level - oversold_level
            # Avoid division by zero if levels are the same
            if range_span > 0:
                score = max(
                    0.0, min(1.0, (overbought_level - latest_k) / range_span)
                )
            else:
                score = 0.5 # Default score if levels are identical

        confidence = round(score, 4)
        result = {
            "symbol": symbol,
            "verdict": verdict,
            "confidence": confidence,
            "value": latest_k,
            "details": {"k": latest_k, "d": latest_d},
            "score": score,
            "agent_name": agent_name,
        }

    # Cache and track
    await redis_client.set(cache_key, result, ex=3600)
    await tracker.update("technical", agent_name, "implemented")
    return result
