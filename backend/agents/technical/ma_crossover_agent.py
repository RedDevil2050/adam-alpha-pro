import pandas as pd
from backend.utils.data_provider import fetch_ohlcv_series
from backend.utils.cache_utils import get_redis_client
from backend.agents.technical.utils import tracker
from datetime import datetime, timedelta # Added
from backend.agents.decorators import standard_agent_execution

agent_name = "ma_crossover_agent"
AGENT_CATEGORY = "technical"  # Define category for the decorator


@standard_agent_execution(
    agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=3600
)
async def run(symbol: str, agent_outputs: dict = None, short_window: int = 50, long_window: int = 200) -> dict:
    # Decorator handles cache check, so remove manual cache logic
    
    # Fetch OHLCV data
    end_date = datetime.now().strftime("%Y-%m-%d") # Added
    start_date = (datetime.now() - timedelta(days=long_window + 50)).strftime("%Y-%m-%d") # Added, ensure enough data for longest window + buffer
    df = await fetch_ohlcv_series(symbol, start_date, end_date) # Modified
    if df is None or df.empty or len(df) < long_window:
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
        # Compute moving averages
        short_ma = close.rolling(window=short_window, min_periods=short_window).mean()
        long_ma = close.rolling(window=long_window, min_periods=long_window).mean()

        last_short = short_ma.iloc[-1]
        last_long = long_ma.iloc[-1]
        prev_short = short_ma.iloc[-2]
        prev_long = long_ma.iloc[-2]

        # Determine crossover
        if prev_short <= prev_long and last_short > last_long:
            score = 1.0
            verdict = "BUY"
        elif prev_short >= prev_long and last_short < last_long:
            score = 0.0
            verdict = "AVOID"
        else:
            score = 0.5
            verdict = "HOLD"

        result = {
            "symbol": symbol,
            "verdict": verdict,
            "confidence": score,
            "value": round(last_short - last_long, 4),
            "details": {
                "short_ma": round(last_short, 4),
                "long_ma": round(last_long, 4),
            },
            "score": score,
            "agent_name": agent_name,
        }

    # Decorator handles caching and tracker update
    return result
