"""Decorators for standardizing agent execution patterns."""

import asyncio
import functools
import json
import inspect
from loguru import logger
from backend.utils.cache_utils import get_redis_client
from backend.monitor.tracker import get_tracker
from datetime import datetime
import numpy as np
import pandas as pd
from decimal import Decimal
from pydantic import BaseModel

# Helper function for robust JSON serialization
def robust_json_serializer(obj):
    if isinstance(obj, (datetime, pd.Timestamp)):
        return obj.isoformat()
    if isinstance(obj, np.integer):
        return int(obj)
    # Handle np.floating first, then Python floats for NaN/Infinity
    if isinstance(obj, np.floating):
        if np.isnan(obj):
            return None
        if np.isinf(obj):
            # Represent infinity as a string, as JSON standard doesn't support Infinity literal
            return "Infinity" if obj > 0 else "-Infinity"
        return float(obj)
    if isinstance(obj, float): # Handle standard Python floats for NaN/Infinity
        if np.isnan(obj): # Use np.isnan for Python floats too for consistency
            return None
        if np.isinf(obj): # Use np.isinf for Python floats too
            return "Infinity" if obj > 0 else "-Infinity"
        return obj # Return the float if it's a normal number
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, BaseModel): # Check for Pydantic models
        try:
            return obj.model_dump() # pydantic v2
        except AttributeError:
            return obj.dict() # pydantic v1
    if isinstance(obj, Decimal): # Handle Decimal type
        return float(obj)
    
    # If it's a standard Python type that json.dumps can handle, return it directly.
    # This check should come after specific type handlers like float for NaN/Inf.
    if isinstance(obj, (dict, list, str, int, bool, type(None))):
        return obj
        
    # Last resort for any other unhandled type
    try:
        # It's generally safer to avoid str(obj) if it's not a known serializable structure,
        # as str(obj) might not be a valid JSON component or could be misleading.
        # However, if we must serialize, provide a clear indication of type.
        logger.warning(f"robust_json_serializer: Attempting to convert unhandled type {type(obj)} to string. Value snippet: {str(obj)[:100]}")
        return f"UNSERIALIZABLE_TYPE_{type(obj).__name__}:{str(obj)}"
    except Exception as e:
        logger.error(f"robust_json_serializer: Failed to convert object of type {type(obj)} to string: {e}")
        # Raising TypeError here will be caught by the caller of json.dumps
        raise TypeError(f"Object of type {type(obj).__name__} could not be converted to string for JSON serialization by robust_json_serializer")


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
                # Get Redis client instance - always use the synchronous version in test mode
                redis_client = get_redis_client()
                
                # 1. Cache Check
                
                _raw_cache_val = None
                if hasattr(redis_client.get, "__await__"): # Check if the 'get' method itself is awaitable
                    _raw_cache_val = await redis_client.get(cache_key)
                else: # 'get' method is synchronous (but might return a coroutine)
                    _raw_cache_val = redis_client.get(cache_key)

                _resolved_cache_val = None
                if asyncio.iscoroutine(_raw_cache_val): # Resolve if the obtained value is a coroutine
                    _resolved_cache_val = await _raw_cache_val
                else:
                    _resolved_cache_val = _raw_cache_val
                
                # Proceed if _resolved_cache_val is not None (could be empty string, which is handled by json.loads)
                if _resolved_cache_val is not None:
                    _data_to_load = _resolved_cache_val
                    if isinstance(_data_to_load, bytes): # Decode if cache returned bytes
                        _data_to_load = _data_to_load.decode('utf-8') 

                    if isinstance(_data_to_load, str): # Ensure it's a string for json.loads
                        try:
                            cached_result = json.loads(_data_to_load)
                            logger.debug(f"Cache hit for {cache_key}")
                            # Note: Original code's tracker update for cache hit might be elsewhere or in finally block
                            return cached_result 
                        except json.JSONDecodeError as e:
                            logger.warning(f"Failed to decode cached JSON for {cache_key}. Data: '{_data_to_load!r}'. Error: {e}. Fetching fresh data.")
                            # Fall through to treat as cache miss
                    else:
                        # If _resolved_cache_val was not None, but not bytes or str after processing
                        logger.warning(f"Cached data for {cache_key} is of unexpected type: {type(_data_to_load)}. Value: '{_data_to_load!r}'. Fetching fresh data.")
                        # Fall through to treat as cache miss
                
                # If we reach here, it implies a cache miss:
                # - _resolved_cache_val was None initially
                # - Or, it was not a string/bytes
                # - Or, json.loads failed
                logger.debug(f"Cache miss for {cache_key}")
                # 2. Execute Core Logic
                # Attempt to execute the agent function
                try:
                    # Execute the function first
                    executed_func_result = func(*args, **kwargs)
                    # Then, check if the result is a coroutine and await it if so
                    if asyncio.iscoroutine(executed_func_result):
                        result = await executed_func_result
                    else:
                        result = executed_func_result

                    # Ensure agent_name is in the result before returning/caching
                    if result and "agent_name" not in result:
                        result["agent_name"] = agent_name

                    # If execution successful, cache the result
                    if result is not None and redis_client:
                        # 3. Cache Result (only on success/valid data)
                        if result and result.get("verdict") not in ["ERROR", "NO_DATA", None]:
                            try:
                                # Handle both sync and async set methods
                                cache_data = json.dumps(result, default=robust_json_serializer)
                                
                                # Call the method, then check if the result is awaitable
                                set_operation_result = redis_client.set(cache_key, cache_data, ex=cache_ttl)
                                if inspect.isawaitable(set_operation_result):
                                    await set_operation_result
                                
                                logger.debug(f"Cached result for {cache_key} with TTL {cache_ttl}s")
                            except TypeError as json_err:
                                logger.error(f"Failed to serialize result for {cache_key} to JSON using robust_json_serializer: {json_err}. Result not cached.")
                            except Exception as cache_err:
                                logger.error(f"Failed to set cache for {cache_key}: {cache_err}. Result not cached.")                        # 4. Update Tracker
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

                            if current_symbol and hasattr(tracker_instance, "update_agent_status"):
                                # Handle both sync and async tracker methods
                                # Call the method, then check if the result is awaitable
                                update_status_result = tracker_instance.update_agent_status(
                                    category, agent_name, current_symbol, status, result
                                )
                                if inspect.isawaitable(update_status_result):
                                    await update_status_result
                                
                                logger.debug(f"Tracker updated for {agent_name} ({current_symbol}): {status}")
                            else:
                                logger.warning(f"Skipping tracker update for {agent_name} due to missing symbol or tracker method.")

                        except ImportError:
                            logger.warning("Tracker module not found or get_tracker failed. Skipping tracker update.")
                        except AttributeError:
                            logger.warning(f"Tracker instance missing 'update_agent_status' method. Skipping tracker update.")
                        except Exception as tracker_err:
                            logger.warning(f"Failed to update tracker for {agent_name} ({symbol}): {tracker_err}")

                    return result # Return potentially modified result

                except Exception as e:
                    # 5. Standard Error Handling
                    # Log the specific agent name causing the error
                    logger.exception(f"Error executing agent {agent_name} for symbol {symbol}: {e}")
                    error_result = {
                        "symbol": symbol,
                        "verdict": "ERROR",
                        "confidence": 0.0,
                        "value": None,
                        "details": {"error": str(e)}, # Store the error message in details
                        "error": str(e), # Keep the top-level error for now, or decide if it's redundant
                        "agent_name": agent_name,
                    }
                    # Ensure agent_name is added in error case (already done)                    # Try to update tracker even if the main agent logic failed
                    try:
                        tracker_instance = get_tracker()
                        status = "error"
                        if symbol and hasattr(tracker_instance, "update_agent_status"):
                            # Handle both sync and async tracker methods
                            # Call the method, then check if the result is awaitable
                            error_update_status_result = tracker_instance.update_agent_status(
                                category, agent_name, symbol, status, error_result
                            )
                            if inspect.isawaitable(error_update_status_result):
                                await error_update_status_result
                            
                            logger.debug(f"Tracker updated for {agent_name} ({symbol}): {status} (after main exception)")
                        else:
                            logger.warning(f"Skipping tracker update for {agent_name} after exception due to missing symbol or tracker method.")
                    except (ImportError, AttributeError) as tracker_err:
                        logger.warning(f"Tracker update failed during error handling: {tracker_err}")
                    except Exception as tracker_err:
                        logger.warning(f"Failed to update tracker during exception handling: {tracker_err}")

                    return error_result

            except Exception as e:
                # Outer exception handling (e.g., Redis connection error)
                logger.exception(f"Outer error in decorator for agent {agent_name}, symbol {symbol}: {e}")
                error_result = {
                    "symbol": symbol,
                    "verdict": "ERROR",
                    "confidence": 0.0,
                    "value": None,
                    "details": {"error": f"Decorator execution error: {e}"}, # Store the error message in details
                    "error": f"Decorator execution error: {e}", # Keep top-level error
                    "agent_name": agent_name, # Ensure agent_name is here too
                }                # Attempt tracker update even for outer errors
                try:
                    tracker_instance = get_tracker()
                    if symbol and hasattr(tracker_instance, "update_agent_status"):
                        # Handle both sync and async tracker methods
                        # Call the method, then check if the result is awaitable
                        outer_error_update_status_result = tracker_instance.update_agent_status(
                            category, agent_name, symbol, "error", error_result
                        )
                        if inspect.isawaitable(outer_error_update_status_result):
                            await outer_error_update_status_result
                        
                        logger.debug(f"Tracker updated for {agent_name} ({symbol}): error (after outer exception)")
                except Exception as tracker_err:
                    logger.warning(f"Tracker update failed during outer error handling: {tracker_err}")
                return error_result

        return wrapper
    return decorator
