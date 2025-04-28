"""Decorators for standardizing agent execution patterns."""

import functools
import json
from loguru import logger
from backend.utils.cache_utils import redis_client
# Assuming tracker is accessible globally or passed differently.
# If tracker needs specific instance per category/agent, this needs adjustment.
# from backend.monitor.tracker import tracker # Example import path

def standard_agent_execution(agent_name: str, category: str, cache_ttl: int = 3600):
    """
    Decorator to handle standard agent execution boilerplate:
    - Cache checking
    - Error handling
    - Standard result formatting (success/error)
    - Cache setting on success
    - Tracker updates (placeholder - needs refinement based on tracker implementation)
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs): # Accept symbol and any other args/kwargs
            # Extract symbol, assuming it's the first positional argument
            # This might need adjustment if agents have different signatures
            if not args:
                 logger.error(f"Agent {agent_name} called without symbol argument.")
                 # Return error or raise? Returning standard error for now.
                 return {
                    "symbol": None, # Cannot determine symbol
                    "verdict": "ERROR",
                    "confidence": 0.0,
                    "value": None,
                    "details": {},
                    "error": "Agent called without symbol argument.",
                    "agent_name": agent_name
                 }

            symbol = args[0]
            cache_key = f"{agent_name}:{symbol}"

            try:
                # 1. Cache Check
                cached_data = await redis_client.get(cache_key)
                if cached_data:
                    try:
                        # Attempt to deserialize cached data
                        cached_result = json.loads(cached_data)
                        logger.debug(f"Cache hit for {cache_key}")
                        # Potentially add cache hit monitoring here
                        return cached_result
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to decode cached JSON for {cache_key}. Fetching fresh data.")
                        # Proceed to fetch fresh data if cache is corrupted

                logger.debug(f"Cache miss for {cache_key}")
                # 2. Execute Core Logic
                # Pass through symbol and any extra args/kwargs (like agent_outputs)
                result = await func(*args, **kwargs)

                # 3. Cache Result (only on success/valid data)
                if result and result.get("verdict") not in ["ERROR", "NO_DATA", None]:
                    try:
                        # Serialize result before caching
                        await redis_client.set(cache_key, json.dumps(result), ex=cache_ttl)
                        logger.debug(f"Cached result for {cache_key} with TTL {cache_ttl}s")
                        # Potentially add cache miss/set monitoring here
                    except TypeError as json_err:
                         logger.error(f"Failed to serialize result for {cache_key} to JSON: {json_err}. Result not cached.")
                    except Exception as cache_err:
                         logger.error(f"Failed to set cache for {cache_key}: {cache_err}. Result not cached.")


                # 4. Update Tracker (Placeholder - adjust based on actual tracker implementation)
                # This needs a reliable way to access the correct tracker instance.
                # Example:
                # try:
                #     from backend.monitor.tracker import get_tracker # Or however it's accessed
                #     tracker_instance = get_tracker()
                #     status = "success" if result.get("verdict") != "ERROR" else "error"
                #     tracker_instance.update_agent_status(category, agent_name, symbol, status)
                # except Exception as tracker_err:
                #     logger.warning(f"Failed to update tracker for {agent_name} ({symbol}): {tracker_err}")

                return result

            except Exception as e:
                # 5. Standard Error Handling
                logger.exception(f"Error executing agent {agent_name} for symbol {symbol}: {e}")
                # Return standard error format
                return {
                    "symbol": symbol,
                    "verdict": "ERROR",
                    "confidence": 0.0,
                    "value": None,
                    "details": {},
                    "error": str(e),
                    "agent_name": agent_name
                }
        return wrapper
    return decorator
