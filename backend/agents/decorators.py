import functools
from backend.utils.cache_utils import redis_client
from loguru import logger
# Assuming tracker is accessible globally or passed differently.
# For now, commenting out direct tracker import/usage within the decorator.
# A more robust solution might involve passing the tracker or using a context manager.
# from backend.agents.risk.utils import tracker # Adjust path as needed

def standard_agent_execution(agent_name: str, category: str, cache_ttl: int = 3600):
    """
    Decorator to handle standard agent execution boilerplate:
    - Cache checking
    - Error handling
    - Result caching (on success)
    - Standard error formatting
    - (Optional/Future: Tracker updates)
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(symbol: str, *args, **kwargs): # Accept potential agent_outputs etc.
            cache_key = f"{agent_name}:{symbol}"
            try:
                # 1. Cache Check
                cached = await redis_client.get(cache_key)
                if cached:
                    logger.debug(f"Cache hit for {agent_name} on {symbol}")
                    return cached
                logger.debug(f"Cache miss for {agent_name} on {symbol}")

                # 2. Execute Core Logic
                # Pass through any extra args/kwargs (like agent_outputs)
                result = await func(symbol, *args, **kwargs)

                # 3. Cache Result (only on success/valid data)
                # Do not cache ERROR or NO_DATA verdicts
                if result and result.get("verdict") not in ["ERROR", "NO_DATA"]:
                     logger.debug(f"Setting cache for {agent_name} on {symbol}")
                     await redis_client.set(cache_key, result, ex=cache_ttl)
                elif result and result.get("verdict") == "NO_DATA":
                    logger.warning(f"No data found for {agent_name} on {symbol}. Not caching.")
                elif result and result.get("verdict") == "ERROR":
                     logger.error(f"Error in {agent_name} for {symbol}. Not caching. Error: {result.get('error')}")


                # 4. Update Tracker (Placeholder - needs proper implementation)
                # This might need to be handled outside the decorator or passed in.
                # try:
                #     # Assuming tracker is globally accessible or configured
                #     from backend.agents.risk.utils import tracker # Example path
                #     tracker.update(category, agent_name, "implemented")
                # except Exception as tracker_error:
                #     logger.warning(f"Failed to update tracker for {agent_name}: {tracker_error}")

                return result

            except Exception as e:
                # 5. Standard Error Handling
                logger.exception(f"Unhandled exception in agent {agent_name} for {symbol}: {e}")
                # Return standard error format
                return {
                    "symbol": symbol,
                    "verdict": "ERROR",
                    "confidence": 0.0,
                    "value": None,
                    "details": {},
                    "error": f"Unhandled exception: {str(e)}", # Provide more context
                    "agent_name": agent_name
                }
        return wrapper
    return decorator
