"""Decorators for standardizing agent execution patterns."""

import functools
import json
from loguru import logger
from backend.utils.cache_utils import redis_client
# Import the tracker access function (adjust path if needed)
from backend.monitor.tracker import get_tracker

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
            result = None # Initialize result to handle potential early exits

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

                # --- 4. Update Tracker --- Start
                try:
                    tracker_instance = get_tracker()
                    status = "error" # Default to error
                    if result and result.get("verdict") not in ["ERROR", "NO_DATA", None]:
                        status = "success"
                    elif result and result.get("verdict") == "NO_DATA":
                        status = "no_data"

                    # Ensure symbol is available even in case of early exit errors
                    current_symbol = symbol # Captured at the start of the wrapper
                    if result and "symbol" in result:
                        current_symbol = result["symbol"] # Use symbol from result if available

                    if current_symbol: # Only update if we have a symbol
                        # Assuming an update method like this exists:
                        await tracker_instance.update_agent_status(category, agent_name, current_symbol, status, result) # Pass full result
                        logger.debug(f"Tracker updated for {agent_name} ({current_symbol}): {status}")
                    else:
                        logger.warning(f"Skipping tracker update for {agent_name} due to missing symbol.")

                except ImportError:
                    logger.warning("Tracker module (backend.monitor.tracker) not found or get_tracker failed. Skipping tracker update.")
                except AttributeError:
                     logger.warning(f"Tracker instance from get_tracker() missing 'update_agent_status' method. Skipping tracker update.")
                except Exception as tracker_err:
                    # Log tracker-specific errors without failing the agent execution
                    logger.warning(f"Failed to update tracker for {agent_name} ({symbol}): {tracker_err}")
                # --- 4. Update Tracker --- End

                return result # Return the original agent result

            except Exception as e:
                # 5. Standard Error Handling
                logger.exception(f"Error executing agent {agent_name} for symbol {symbol}: {e}")
                # Construct error result
                error_result = {
                    "symbol": symbol,
                    "verdict": "ERROR",
                    "confidence": 0.0,
                    "value": None,
                    "details": {},
                    "error": str(e),
                    "agent_name": agent_name
                }

                # --- Attempt Tracker Update on General Exception --- Start
                # Also try to update tracker even if the main agent logic failed
                try:
                    tracker_instance = get_tracker()
                    status = "error"
                    # Use the symbol captured at the start
                    if symbol:
                        await tracker_instance.update_agent_status(category, agent_name, symbol, status, error_result) # Pass error result
                        logger.debug(f"Tracker updated for {agent_name} ({symbol}): {status} (after main exception)")
                    else:
                         logger.warning(f"Skipping tracker update for {agent_name} after exception due to missing symbol.")
                except ImportError:
                    logger.warning("Tracker module not found during exception handling. Skipping tracker update.")
                except AttributeError:
                     logger.warning(f"Tracker instance missing 'update_agent_status' during exception handling. Skipping tracker update.")
                except Exception as tracker_err_on_fail:
                    logger.warning(f"Failed to update tracker during exception handling for {agent_name} ({symbol}): {tracker_err_on_fail}")
                # --- Attempt Tracker Update on General Exception --- End

                return error_result # Return the error result

        return wrapper
    return decorator
