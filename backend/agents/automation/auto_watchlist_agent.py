from backend.utils.data_provider import fetch_price_series
from backend.utils.cache_utils import get_redis_client
from backend.config.settings import settings
from backend.agents.automation.utils import tracker
import pandas as pd
import numpy as np
import json # Import json
from loguru import logger # Add logger import

agent_name = "auto_watchlist_agent"


async def run(symbol: str, agent_outputs: dict = {}) -> dict:
    redis_client = await get_redis_client()
    cache_key = f"{agent_name}:{symbol}"
    cached = await redis_client.get(cache_key)
    if cached:
        try:
            return json.loads(cached)
        except json.JSONDecodeError:
            pass # Fall through to recompute if cache is corrupt

    # Fetch 30-day price series to check momentum
    prices = await fetch_price_series(symbol, source_preference=["api", "scrape"])

    # Evaluate signals from agent_outputs
    flags = []
    for key, out in agent_outputs.items():
        if out.get("verdict") in ("STRONG_BUY", "BUY", "POSITIVE"):
            flags.append(key)

    # Simple momentum: last price > first, ensure prices is a non-empty Series or list of numbers
    if isinstance(prices, pd.Series) and not prices.empty:
        # Ensure numeric types before comparison if series can hold objects
        if pd.api.types.is_numeric_dtype(prices.dtype): # Check dtype of series
            if prices.iloc[-1] > prices.iloc[0]:
                flags.append("Positive Momentum")
        else:
            # Attempt to convert to numeric if possible, coercing errors
            numeric_prices = pd.to_numeric(prices, errors='coerce')
            if not numeric_prices.empty and not numeric_prices.isnull().all() and pd.api.types.is_numeric_dtype(numeric_prices.dtype):
                 # Check first and last valid numbers
                first_valid = numeric_prices.dropna().iloc[0] if not numeric_prices.dropna().empty else None
                last_valid = numeric_prices.dropna().iloc[-1] if not numeric_prices.dropna().empty else None
                if first_valid is not None and last_valid is not None and last_valid > first_valid:
                    flags.append("Positive Momentum")
                elif not (first_valid is not None and last_valid is not None) : # only log if we couldn't compare
                    logger.warning(f"auto_watchlist_agent: Prices series for {symbol} could not be reliably converted to numeric for momentum check.")
            else:
                logger.warning(f"auto_watchlist_agent: Prices series for {symbol} is not numeric and could not be converted, skipping momentum.")

    elif isinstance(prices, list) and len(prices) >= 2: # Check if list and has at least two elements
        # Further check if elements are numeric before comparison
        first_price = prices[0]
        last_price = prices[-1]
        if isinstance(first_price, (int, float)) and isinstance(last_price, (int, float)):
            if last_price > first_price:
                flags.append("Positive Momentum")
        else:
            logger.warning(f"auto_watchlist_agent: Prices list for {symbol} contains non-numeric elements at boundaries, skipping momentum.")
    elif prices is not None and not isinstance(prices, pd.Series) and not isinstance(prices, list): # Catch other truthy but unhandled price types
        logger.warning(f"auto_watchlist_agent: Unhandled prices type for {symbol}: {type(prices)}, skipping momentum.")

    verdict = "WATCH" if flags else "IGNORE"
    confidence = min(len(flags) / (len(agent_outputs) + 1), 1.0)

    result = {
        "symbol": symbol,
        "verdict": verdict,
        "confidence": round(confidence, 4),
        "value": len(flags),
        "details": {"signals": flags},
        "score": confidence,
        "agent_name": agent_name,
    }

    await redis_client.set(cache_key, json.dumps(result), ex=settings.agent_cache_ttl)
    tracker.update("automation", agent_name, "implemented")
    return result
