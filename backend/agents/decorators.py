"""Decorators for standardizing agent execution patterns."""

import asyncio
import functools
import json
from loguru import logger
from backend.utils.cache_utils import get_redis_client

# Import the tracker access function (adjust path if needed)
from backend.monitor.tracker import get_tracker


def standard_agent_execution(agent_name: str, category: str, cache_ttl: int = 3600):
    """
    Decorator to handle standard agent execution boilerplate:
    - Cache checking
    - Error handling
    - Standard result formatting (success/error)
    - Cache setting on success
    - Tracker updates
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if not args:
                logger.error(f"Agent {agent_name} called without symbol argument.")
                return {
                    "symbol": None,
                    "verdict": "ERROR",
                    "confidence": 0.0,
                    "value": None,
                    "details": {},
                    "error": "Agent called without symbol argument.",
                    "agent_name": agent_name,
                }

            symbol = args[0]
            cache_key = f"{agent_name}:{symbol}"
            result = None

            try:
                # Get Redis client instance
                redis_client = await get_redis_client()
                
                # 1. Cache Check
                cached_data = await redis_client.get(cache_key)
                if cached_data:
                    try:
                        cached_result = json.loads(cached_data)
                        logger.debug(f"Cache hit for {cache_key}")
                        return cached_result
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to decode cached JSON for {cache_key}. Fetching fresh data.")

                logger.debug(f"Cache miss for {cache_key}")
                # 2. Execute Core Logic
                # Attempt to execute the agent function
                try:
                    # Ensure the decorated function is awaited if it's a coroutine
                    if asyncio.iscoroutinefunction(func):
                        result = await func(*args, **kwargs)
                    else:
                        # Handle synchronous functions if necessary, though less common here
                        # This part might need adjustment based on actual usage
                        result = func(*args, **kwargs) # Assuming sync functions are possible

                    # If execution successful, cache the result
                    if result is not None and redis_client:
                        # 3. Cache Result (only on success/valid data)
                        if result and result.get("verdict") not in ["ERROR", "NO_DATA", None]:
                            try:
                                await redis_client.set(cache_key, json.dumps(result), ex=cache_ttl)
                                logger.debug(f"Cached result for {cache_key} with TTL {cache_ttl}s")
                            except TypeError as json_err:
                                logger.error(f"Failed to serialize result for {cache_key} to JSON: {json_err}. Result not cached.")
                            except Exception as cache_err:
                                logger.error(f"Failed to set cache for {cache_key}: {cache_err}. Result not cached.")

                        # 4. Update Tracker
                        try:
                            tracker_instance = get_tracker()
                            status = "error"  # Default to error
                            if result and result.get("verdict") not in ["ERROR", "NO_DATA", None]:
                                status = "success"
                            elif result and result.get("verdict") == "NO_DATA":
                                status = "no_data"

                            current_symbol = symbol
                            if result and "symbol" in result:
                                current_symbol = result["symbol"]

                            if current_symbol:
                                await tracker_instance.update_agent_status(
                                    category, agent_name, current_symbol, status, result
                                )
                                logger.debug(f"Tracker updated for {agent_name} ({current_symbol}): {status}")
                            else:
                                logger.warning(f"Skipping tracker update for {agent_name} due to missing symbol.")

                        except ImportError:
                            logger.warning("Tracker module not found or get_tracker failed. Skipping tracker update.")
                        except AttributeError:
                            logger.warning(f"Tracker instance missing 'update_agent_status' method. Skipping tracker update.")
                        except Exception as tracker_err:
                            logger.warning(f"Failed to update tracker for {agent_name} ({symbol}): {tracker_err}")

                        return result

                except Exception as e:
                    # 5. Standard Error Handling
                    logger.exception(f"Error executing agent {agent_name} for symbol {symbol}: {e}")
                    error_result = {
                        "symbol": symbol,
                        "verdict": "ERROR",
                        "confidence": 0.0,
                        "value": None,
                        "details": {},
                        "error": str(e),
                        "agent_name": agent_name,
                    }

                    # Try to update tracker even if the main agent logic failed
                    try:
                        tracker_instance = get_tracker()
                        status = "error"
                        if symbol:
                            await tracker_instance.update_agent_status(
                                category, agent_name, symbol, status, error_result
                            )
                            logger.debug(f"Tracker updated for {agent_name} ({symbol}): {status} (after main exception)")
                        else:
                            logger.warning(f"Skipping tracker update for {agent_name} after exception due to missing symbol.")
                    except (ImportError, AttributeError) as tracker_err:
                        logger.warning(f"Tracker update failed during error handling: {tracker_err}")
                    except Exception as tracker_err:
                        logger.warning(f"Failed to update tracker during exception handling: {tracker_err}")

                    return error_result

            except Exception as e:
                # 5. Standard Error Handling
                logger.exception(f"Error executing agent {agent_name} for symbol {symbol}: {e}")
                error_result = {
                    "symbol": symbol,
                    "verdict": "ERROR",
                    "confidence": 0.0,
                    "value": None,
                    "details": {},
                    "error": str(e),
                    "agent_name": agent_name,
                }

                # Try to update tracker even if the main agent logic failed
                try:
                    tracker_instance = get_tracker()
                    status = "error"
                    if symbol:
                        await tracker_instance.update_agent_status(
                            category, agent_name, symbol, status, error_result
                        )
                        logger.debug(f"Tracker updated for {agent_name} ({symbol}): {status} (after main exception)")
                    else:
                        logger.warning(f"Skipping tracker update for {agent_name} after exception due to missing symbol.")
                except (ImportError, AttributeError) as tracker_err:
                    logger.warning(f"Tracker update failed during error handling: {tracker_err}")
                except Exception as tracker_err:
                    logger.warning(f"Failed to update tracker during exception handling: {tracker_err}")

                return error_result

        return wrapper
    return decorator
