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
from backend.models.common_models import Verdict, VerdictType # Import VerdictType

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
            symbol = None
            if args:
                symbol = args[0]
            elif 'symbol' in kwargs:
                symbol = kwargs['symbol']
            
            if not symbol:
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

            cache_key = f"{agent_name}:{symbol}"
            result = None
            
            try:
                # Get Redis client instance
                redis_client = await get_redis_client()
                client_to_use = redis_client # client_to_use is the async-ready client

                # 1. Cache Check
                _resolved_cache_val = None
                if client_to_use: # Ensure client was obtained
                    # Assuming client_to_use.get is directly awaitable
                    _raw_cache_val = await client_to_use.get(cache_key)
                    # _raw_cache_val is the actual value or None, not a coroutine.
                    _resolved_cache_val = _raw_cache_val
                
                if _resolved_cache_val is not None:
                    _data_to_load = _resolved_cache_val
                    if isinstance(_data_to_load, bytes): # Decode if cache returned bytes
                        _data_to_load = _data_to_load.decode('utf-8') 

                    if isinstance(_data_to_load, str): # Ensure it's a string for json.loads
                        try:
                            cached_result = json.loads(_data_to_load)
                            logger.debug(f"Cache hit for {cache_key}")
                            return cached_result 
                        except json.JSONDecodeError as e:
                            logger.warning(f"Failed to decode cached JSON for {cache_key}. Data: '{_data_to_load!r}'. Error: {e}. Fetching fresh data.")
                    else:
                        logger.warning(f"Cached data for {cache_key} is of unexpected type: {type(_data_to_load)}. Value: '{_data_to_load!r}'. Fetching fresh data.")
                
                logger.debug(f"Cache miss for {cache_key}")
                # 2. Execute Core Logic
                try:
                    # Execute the function first
                    
                    # Original kwargs from the user's call to the decorated function
                    # _func_kwargs = kwargs.copy() # REMOVED
                    # Extract market_provider from user_kwargs if present, as it's handled specially.
                    # _market_provider = _func_kwargs.pop('market_context_provider', None) # REMOVED

                    # Inspect the signature of the wrapped function
                    func_sig = inspect.signature(func)
                    func_params = func_sig.parameters

                    # Start with an empty dict for kwargs to be passed to the actual function
                    call_kwargs = {}

                    # 1. Populate with original user-provided kwargs if accepted by func.
                    #    The decorator will then inject/override core dependencies.
                    for key, value in kwargs.items(): # Use original kwargs from wrapper's signature
                        if key in func_params:
                            call_kwargs[key] = value
                    
                    # 2. Decorator-injected/managed arguments.
                    # These are essential for AgentBase and are provided/overridden by the decorator
                    # if the wrapped function declares them in its signature.

                    # Agent Name (parameter for the decorator itself)
                    if 'name' in func_params:
                        call_kwargs['name'] = agent_name

                    # Cache Client (obtained earlier in the decorator)
                    if 'cache_client' in func_params:
                        call_kwargs['cache_client'] = client_to_use

                    # Logger (from the decorator's scope, typically loguru instance)
                    # AgentBase constructor expects 'logger'.
                    if 'logger' in func_params:
                        call_kwargs['logger'] = logger 
                    elif 'logger_instance' in func_params: # Support alternative naming if used by func
                        call_kwargs['logger_instance'] = logger
                    
                    # Settings, DataProvider, and MarketContextProvider
                    _settings_instance = None
                    _data_provider_instance = None
                    # mcp_instance will be defined if market_context_provider is successfully created

                    # Step 1: Determine if settings need to be loaded and load them.
                    needs_settings_loaded = (
                        'settings' in func_params or
                        'data_provider' in func_params or
                        'market_context_provider' in func_params # MCP needs settings, often via DP
                    )

                    if needs_settings_loaded:
                        from backend.config import settings as global_settings_accessor
                        _settings_instance = global_settings_accessor.settings
                        if not _settings_instance:
                            logger.error(f"Agent {agent_name} decorator: Global settings failed to load. Required by function {func.__name__} for settings, data_provider, or market_context_provider.")
                        # If the function explicitly asks for settings, provide it
                        if 'settings' in func_params:
                            call_kwargs['settings'] = _settings_instance

                    # Step 2: Instantiate DataProvider if needed and possible.
                    # DataProvider is needed if 'data_provider' is in func_params OR 'market_context_provider' is (as MCP depends on it).
                    needs_data_provider = 'data_provider' in func_params or 'market_context_provider' in func_params
                    
                    if needs_data_provider:
                        if _settings_instance: # DP requires settings to have loaded successfully
                            from backend.data.providers.unified_provider import UnifiedDataProvider
                            # UnifiedDataProvider does not take settings in its constructor
                            _data_provider_instance = UnifiedDataProvider() 
                            
                            # If the function explicitly asks for data_provider, provide it.
                            if 'data_provider' in func_params:
                                call_kwargs['data_provider'] = _data_provider_instance
                        else:
                            # This logs if settings failed to load AND data_provider (or MCP needing DP) was requested.
                            logger.error(f"Agent {agent_name} decorator: Cannot create data_provider for {func.__name__} due to missing settings.")
                            # _data_provider_instance remains None

                    # Step 3: Instantiate MarketContextProvider if needed and possible.
                    if 'market_context_provider' in func_params:
                        mcp_instance_to_pass = None # Initialize to None, to be passed if requested
                        if _data_provider_instance and _settings_instance: # MCP requires both DP and settings
                            from backend.market.context import MarketContext
                            try:
                                # Attempt to get/create the MarketContext instance
                                mcp_instance_val = await MarketContext.get_instance(
                                    data_provider=_data_provider_instance,
                                    settings=_settings_instance
                                )
                                mcp_instance_to_pass = mcp_instance_val # Assign if successful
                            except Exception as e_mcp:
                                logger.error(f"Agent {agent_name} decorator: Failed to instantiate MarketContext for {func.__name__}: {e_mcp}")
                                # mcp_instance_to_pass remains None, will be passed as None
                        else:
                            missing_mcp_deps = []
                            if not _data_provider_instance:
                                missing_mcp_deps.append("data_provider instance (dependency not met or its own settings dependency failed)")
                            if not _settings_instance: # This check is somewhat redundant if DP creation relies on settings, but good for explicit clarity
                                missing_mcp_deps.append("settings instance (dependency not met)")
                            
                            logger.warning(
                                f"Agent {agent_name} decorator: Cannot create market_context_provider for function {func.__name__}. "
                                f"Missing dependencies: {', '.join(missing_mcp_deps) if missing_mcp_deps else 'unknown reason (likely settings or data_provider init failure)'}."
                            )
                            # mcp_instance_to_pass remains None, will be passed as None
                        
                        call_kwargs['market_context_provider'] = mcp_instance_to_pass # Always add to call_kwargs if in func_params
                    
                    executed_func_result = func(*args, **call_kwargs)
                    # Then, check if the result is a coroutine and await it if so
                    if asyncio.iscoroutine(executed_func_result):
                        result = await executed_func_result
                    else:
                        result = executed_func_result

                    # Ensure agent_name is in the result (if it's a Verdict object or dict)
                    if result and isinstance(result, Verdict):
                        if result.agent_name is None:
                            result.agent_name = agent_name
                        # Convert Verdict to dict for caching and further dict-based operations
                        # This is a key change: the decorator will now work with a dict internally
                        # after the agent's core logic returns a Verdict object.
                        # We use robust_json_serializer to prepare for JSON, then json.loads to get a clean dict.
                        result_for_cache_and_dict_ops = json.loads(json.dumps(result, default=robust_json_serializer))
                    elif result and isinstance(result, dict) and "agent_name" not in result:
                        result["agent_name"] = agent_name
                        result_for_cache_and_dict_ops = result # Already a dict
                    elif result is None:
                        result_for_cache_and_dict_ops = None
                    else: # Not a Verdict or dict, or already has agent_name if dict
                        # This case might need specific handling if other types are expected.
                        # For now, assume if not Verdict or dict, it's an error or unhandled.
                        # If it's a simple type, it won't have 'verdict' or 'agent_name'.
                        # Let's assume for now that if it's not None, Verdict, or dict,
                        # it will likely fail subsequent checks or be an error.
                        # If the agent can return other valid types, this logic needs expansion.
                        logger.warning(f"Agent {agent_name} returned unexpected type: {type(result)}. Proceeding, but caching/tracking might be affected.")
                        result_for_cache_and_dict_ops = result # Pass through, but dict operations will fail

                    # If execution successful, cache the result
                    if result_for_cache_and_dict_ops is not None and client_to_use: # Check client_to_use
                        if isinstance(result_for_cache_and_dict_ops, dict) and \
                           result_for_cache_and_dict_ops.get("verdict") not in [VerdictType.ERROR.value, VerdictType.NO_DATA.value, None]:
                            try:
                                cache_data = json.dumps(result_for_cache_and_dict_ops, default=robust_json_serializer)
                                # Assuming client_to_use.set is directly awaitable
                                await client_to_use.set(cache_key, cache_data, ex=cache_ttl)
                                logger.debug(f"Cached result for {cache_key} with TTL {cache_ttl}s")
                            except TypeError as json_err:
                                logger.error(f"Failed to serialize result for {cache_key} to JSON using robust_json_serializer: {json_err}. Result not cached.")
                            except Exception as cache_err:
                                logger.error(f"Failed to set cache for {cache_key}: {cache_err}. Result not cached.")                        # 4. Update Tracker
                        try:
                            tracker_instance = get_tracker()
                            status = "error"  # Default to error
                            current_verdict_val = None
                            if isinstance(result_for_cache_and_dict_ops, dict):
                                current_verdict_val = result_for_cache_and_dict_ops.get("verdict")

                            if current_verdict_val not in [VerdictType.ERROR.value, VerdictType.NO_DATA.value, None]:
                                status = "success"
                            elif current_verdict_val == VerdictType.NO_DATA.value:
                                status = "no_data"

                            current_symbol = symbol
                            if isinstance(result_for_cache_and_dict_ops, dict) and "symbol" in result_for_cache_and_dict_ops:
                                current_symbol = result_for_cache_and_dict_ops["symbol"]
                            elif isinstance(result, Verdict) and result.details and "symbol" in result.details: # Fallback if symbol is in Verdict.details
                                current_symbol = result.details["symbol"]

                            if current_symbol and hasattr(tracker_instance, "update_agent_status"):
                                # Handle both sync and async tracker methods
                                # Call the method, then check if the result is awaitable
                                update_status_result = tracker_instance.update_agent_status(
                                    category, agent_name, current_symbol, status, result_for_cache_and_dict_ops # Pass the dict version
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

                    # IMPORTANT: Return the original 'result' (which could be a Verdict object)
                    # not 'result_for_cache_and_dict_ops', unless the decorator's contract is to always return a dict.
                    return result

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
