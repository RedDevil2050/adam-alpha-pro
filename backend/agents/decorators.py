"""Decorators for standardizing agent execution patterns."""

import functools
import traceback
from loguru import logger
from backend.utils.cache_utils import redis_client
# Assuming tracker is globally accessible or passed differently.
# If tracker needs specific category/agent context, this might need adjustment.
# from backend.agents.intelligence.utils import tracker # Example path, adjust as needed

def standard_agent_execution(agent_name: str, category: str, cache_ttl: int = 3600):
    """
    Decorator to handle standard agent boilerplate:
    - Cache checking
    - Error handling and logging
    - Standardized result formatting (success, NO_DATA, ERROR)
    - Cache setting on success
    - Tracker updates (Placeholder - requires tracker implementation details)
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs): # More flexible args
            # Assume symbol is the first positional argument if present
            symbol = args[0] if args and isinstance(args[0], str) else kwargs.get("symbol", "unknown")
            cache_key = f"{agent_name}:{symbol}"

            try:
                # 1. Cache Check
                cached_str = await redis_client.get(cache_key)
                if cached_str:
                    try:
                        # Attempt to deserialize cached data (assuming JSON string)
                        cached_data = await redis_client.get_json(cache_key)
                        if cached_data:
                             logger.debug(f"Cache hit for {cache_key}")
                             return cached_data
                        else:
                             logger.warning(f"Cache hit for {cache_key} but failed to parse JSON.")
                             # Proceed to execute function if cache is invalid
                    except Exception as e:
                        logger.warning(f"Error reading cache for {cache_key}: {e}. Re-running agent.")
                        # Proceed to execute function if cache is corrupted

                logger.debug(f"Cache miss for {cache_key}. Running agent {agent_name}.")
                # 2. Execute Core Logic
                result = await func(*args, **kwargs) # Pass all args/kwargs

                # Ensure result is a dictionary before proceeding
                if not isinstance(result, dict):
                     logger.error(f"Agent {agent_name} for {symbol} did not return a dictionary. Returned: {type(result)}")
                     # Return a standard error format if the agent's return is invalid
                     return {
                         "symbol": symbol,
                         "verdict": "ERROR",
                         "confidence": 0.0,
                         "value": None,
                         "details": {"error": "Agent implementation returned invalid type."},
                         "error": "Agent implementation returned invalid type.",
                         "agent_name": agent_name
                     }


                # Add agent_name to the result if not already present (for success/NO_DATA)
                if "agent_name" not in result:
                    result["agent_name"] = agent_name

                # 3. Cache Result (only on success, not NO_DATA or ERROR)
                # Check for specific verdicts that indicate success
                successful_verdicts = result.get("verdict") not in ["ERROR", "NO_DATA", None]
                if successful_verdicts:
                    try:
                        await redis_client.set_json(cache_key, result, ex=cache_ttl)
                        logger.debug(f"Cached result for {cache_key} with TTL {cache_ttl}s.")
                    except Exception as e:
                         logger.error(f"Failed to cache result for {agent_name} ({symbol}): {e}")


                # 4. Update Tracker (Placeholder)
                # This needs a proper implementation based on how 'tracker' is managed.
                # Example: tracker.update(category, agent_name, "executed_success" if successful_verdicts else "executed_nodata")
                # logger.debug(f"Tracker update placeholder for {category}/{agent_name}")

                return result

            except Exception as e:
                # 5. Standard Error Handling
                logger.error(f"Error executing agent {agent_name} for {symbol}: {e}
{traceback.format_exc()}")
                # tracker.update(category, agent_name, "execution_error") # Placeholder
                return {
                    "symbol": symbol,
                    "verdict": "ERROR",
                    "confidence": 0.0,
                    "value": None,
                    "details": {"error": str(e)}, # Include error in details
                    "error": str(e),
                    "agent_name": agent_name
                }
        return wrapper
    return decorator
