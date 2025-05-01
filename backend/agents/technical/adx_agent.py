import pandas as pd
from backend.utils.data_provider import fetch_ohlcv_series
from backend.utils.cache_utils import get_redis_client
from backend.agents.technical.utils import tracker
import datetime
from dateutil.relativedelta import relativedelta

agent_name = "adx_agent"


async def run(symbol: str, agent_outputs: dict = None) -> dict:
    cache_key = f"{agent_name}:{symbol}"
    redis_client = await get_redis_client() # Added await
    # 1) Cache check
    cached = await redis_client.get(cache_key)
    if cached:
        return cached

    # 2) Define date range (e.g., 7 months for daily data)
    end_date = datetime.date.today()
    start_date = end_date - relativedelta(months=7)

    # 3) Fetch OHLCV with start/end dates and interval
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
        high = df["high"]
        low = df["low"]
        close = df["close"]
        prev_close = close.shift(1)

        # 4) True Range and ATR
        tr = pd.concat(
            [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
        ).max(axis=1)
        atr = tr.rolling(window=14, min_periods=14).mean()

        # 5) Directional Movements
        up_move = high - high.shift(1)
        down_move = low.shift(1) - low
        plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
        minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)

        # 6) Directional Indicators
        plus_di = 100 * plus_dm.rolling(window=14, min_periods=14).mean() / atr
        minus_di = 100 * minus_dm.rolling(window=14, min_periods=14).mean() / atr

        # 7) DX and ADX
        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
        adx = dx.rolling(window=14, min_periods=14).mean().iloc[-1]
        adx = float(adx)

        # 8) Normalize & Verdict
        if adx > 25:
            score = 1.0
            verdict = "STRONG_TREND"
        elif adx < 20:
            score = 0.0
            verdict = "NO_TREND"
        else:
            score = (adx - 20) / 5.0
            verdict = "TRENDING"

        result = {
            "symbol": symbol,
            "verdict": verdict,
            "confidence": score,
            "value": adx,
            "details": {"adx": adx},
            "score": score,
            "agent_name": agent_name,
        }

    # 9) Cache result for 1 hour
    await redis_client.set(cache_key, result, ex=3600)
    # 10) Update progress tracker
    tracker.update("technical", agent_name, "implemented")

    return result
