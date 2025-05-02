import httpx
import json
import logging
from backend.utils.cache_utils import get_redis_client
from backend.agents.event.utils import tracker
# Import the specific data provider function
from backend.utils.data_provider import fetch_insider_trades

agent_name = "insider_trade_agent"
logger = logging.getLogger(__name__)

async def run(symbol: str) -> dict:
    redis_client = await get_redis_client()
    cache_key = f"{agent_name}:{symbol}"
    cached_data = await redis_client.get(cache_key)
    if cached_data:
        try:
            # Attempt to load cached data
            cached_result = json.loads(cached_data)
            return cached_result
        except json.JSONDecodeError:
            logger.warning(f"Failed to decode cached JSON for {cache_key}. Fetching fresh data.")

    # Fetch insider trade data using the data_provider function
    trades = []
    error_message = None
    try:
        # Use the imported fetch function
        trades_data = await fetch_insider_trades(symbol)
        trades = trades_data if isinstance(trades_data, list) else []

    except Exception as e:
        error_message = str(e)
        logger.exception(f"Error fetching insider trades for {symbol}: {e}")
        result = {
            "symbol": symbol,
            "verdict": "ERROR",
            "confidence": 0.0,
            "value": None,
            "details": {},
            "insider_trades": [], # Ensure key exists even in error
            "error": error_message,
            "agent_name": agent_name,
        }
        # Attempt to cache error state briefly
        try:
            await redis_client.set(cache_key, json.dumps(result), ex=600) # Cache error for 10 mins
        except Exception as cache_err:
            logger.error(f"Failed to cache error state for {cache_key}: {cache_err}")
        return result

    # Process trades if fetched successfully
    if not trades:
        result = {
            "symbol": symbol,
            "verdict": "NEUTRAL", # Changed from NO_DATA for clarity when fetch is successful but empty
            "confidence": 0.5,
            "value": 0,
            "details": {"trades_count": 0},
            "insider_trades": [], # Ensure key exists
            "error": None,
            "agent_name": agent_name,
        }
    else:
        # Score based on number of trades
        count = len(trades)
        # More nuanced scoring/verdict based on trade volume/recency could be added here
        score = min(count / 10.0, 1.0) # Simple count-based score
        verdict = (
            "SIGNIFICANT_ACTIVITY" if score >= 0.6 else
            "MODERATE_ACTIVITY" if score >= 0.3 else
            "LOW_ACTIVITY"
        )
        result = {
            "symbol": symbol,
            "verdict": verdict,
            "confidence": round(score, 4),
            "value": count,
            "details": {"trades_count": count}, # Keep details concise
            "insider_trades": trades, # Include actual trades
            "error": None,
            "agent_name": agent_name,
        }

    # Cache successful result
    try:
        await redis_client.set(cache_key, json.dumps(result), ex=86400) # Cache success for 24h
    except TypeError as json_err:
        logger.error(f"Failed to serialize result for {cache_key} to JSON: {json_err}. Result not cached.")
    except Exception as cache_err:
        logger.error(f"Failed to set cache for {cache_key}: {cache_err}. Result not cached.")

    # Update tracker (assuming tracker is imported and configured)
    try:
        tracker.update("event", agent_name, "implemented") # Simplified tracker update
    except Exception as tracker_err:
        logger.warning(f"Failed to update tracker for {agent_name}: {tracker_err}")

    return result
