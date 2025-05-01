import pandas as pd
from backend.utils.data_provider import fetch_ohlcv_series
from backend.utils.cache_utils import get_redis_client
from backend.agents.technical.utils import tracker
from datetime import datetime, date, timedelta # Import date
from dateutil.relativedelta import relativedelta
from backend.agents.decorators import standard_agent_execution # Import decorator
import json # Import json
from loguru import logger # Import logger

agent_name = "moving_average_agent"


@standard_agent_execution(agent_name=agent_name, category="technical") # Add agent_name
# Correct signature: agent_outputs is second, window is keyword arg
async def run(symbol: str, agent_outputs: dict = None, window: int = 20) -> dict:
    cache_key = f"{agent_name}:{symbol}:{window}"
    redis_client = await get_redis_client() # Await redis client
    # 1) Cache check
    cached_data = await redis_client.get(cache_key)
    if cached_data:
        try:
            # Attempt to decode JSON if it's stored as a string
            cached_result = json.loads(cached_data)
            return cached_result
        except (json.JSONDecodeError, TypeError):
            # Handle cases where cached data is not valid JSON or already a dict
            # If it's already a dict (or other non-string type), return as is
            if isinstance(cached_data, dict):
                return cached_data
            else:
                # Log error or handle unexpected cache format
                logger.warning(f"Invalid cache format for {cache_key}. Re-fetching.")
                # Proceed to fetch data if cache is invalid

    # Define date range
    end_date = date.today() # Use date.today()
    # Calculate start date based on window size + buffer for calculation
    start_date = end_date - timedelta(days=window * 2 + 60) # Increased buffer

    # 2) Fetch OHLCV data - Always fetch, don't rely on agent_outputs for df
    ohlcv_data = await fetch_ohlcv_series(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        interval='1d' # Ensure interval is passed
    )

    # Check if fetched data is a valid DataFrame
    if not isinstance(ohlcv_data, pd.DataFrame) or ohlcv_data.empty or len(ohlcv_data) < window + 1:
        logger.warning(f"[{agent_name}] Insufficient or invalid data for {symbol}. Type: {type(ohlcv_data)}")
        result = {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {"reason": "Insufficient or invalid OHLCV data received"},
            "agent_name": agent_name,
        }
    else:
        # Proceed with calculation using the DataFrame (ohlcv_data)
        close = ohlcv_data["close"]
        ma = close.rolling(window=window, min_periods=window).mean()
        # Calculate slope percentage of MA
        ma_last = ma.iloc[-1]
        ma_prev = ma.iloc[-2]
        slope_pct = (ma_last - ma_prev) / ma_prev if ma_prev != 0 else 0.0

        # Normalize and verdict
        if slope_pct > 0:
            score = min(slope_pct * 10, 1.0)
            verdict = "BUY"
        elif slope_pct < 0:
            score = 0.0
            verdict = "AVOID"
        else:
            score = 0.5
            verdict = "HOLD"

        result = {
            "symbol": symbol,
            "verdict": verdict,
            "confidence": score,
            "value": round(slope_pct, 4),
            "details": {
                "ma_last": round(ma_last, 4),
                "ma_prev": round(ma_prev, 4),
                "slope_pct": round(slope_pct, 4),
            },
            "score": score,
            "agent_name": agent_name,
        }

    # 3) Cache result for 1 hour
    # Ensure result is JSON serializable before caching
    try:
        await redis_client.set(cache_key, json.dumps(result), ex=3600)
    except TypeError as e:
        logger.error(f"Failed to serialize result for caching {cache_key}: {e}")

    # 4) Update progress tracker
    # tracker.update("technical", agent_name, "implemented") # Assuming tracker is correctly set up

    return result
