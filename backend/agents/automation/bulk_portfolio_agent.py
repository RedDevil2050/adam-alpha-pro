import asyncio
from backend.utils.data_provider import fetch_price_series
from backend.orchestrator import run_full_cycle
from backend.utils.cache_utils import get_redis_client
from backend.config.settings import get_settings
from backend.agents.automation.utils import tracker
from loguru import logger
import json

agent_name = "bulk_portfolio_agent"


async def run(symbol_input: str) -> dict:
    """
    Processes a single symbol when called as a category agent.
    The agent's name "bulk_portfolio_agent" might imply it can also be used
    to process a list of symbols if called directly, but this run signature
    is for compatibility with CategoryManager.
    """
    settings = get_settings()
    symbols_to_process = [symbol_input]

    redis_client = await get_redis_client()
    cache_key = f"{agent_name}:{symbol_input}"
    cached_data = await redis_client.get(cache_key)
    if cached_data:
        try:
            return json.loads(cached_data)
        except json.JSONDecodeError:
            logger.warning(f"Failed to decode cached JSON for {cache_key}. Recomputing.")
            # Fall through to recompute

    if not symbols_to_process:
        logger.error(f"No symbol provided to bulk_portfolio_agent for input: {symbol_input}")
        return {
            "symbol": symbol_input,
            "verdict": "ERROR",
            "confidence": 0.0,
            "value": 0,
            "details": {"error": "No symbols to process"},
            "score": 0.0,
            "agent_name": agent_name,
            "error": "No symbols to process"
        }

    try:
        # Using symbols_to_process[0] which is symbol_input
        prices = await fetch_price_series(symbols_to_process[0], source_preference=["api", "scrape"])
        if prices is None or prices.empty:
            logger.warning(f"Initial price fetch for {symbols_to_process[0]} in {agent_name} returned no data.")
            # Depending on requirements, might return NO_DATA or ERROR here.
            # For now, let run_full_cycle handle it or fail.
    except ValueError as e:
        logger.error(f"Failed to fetch initial price series for {symbols_to_process[0]} in {agent_name}: {e}")
        return {
            "symbol": symbol_input,
            "verdict": "ERROR",
            "confidence": 0.0,
            "value": 0,
            "details": {"error": f"Failed to fetch initial price data for {symbols_to_process[0]}: {e}"},
            "score": 0.0,
            "agent_name": agent_name,
            "error": f"Failed to fetch initial price data for {symbols_to_process[0]}: {e}"
        }
    except Exception as e:
        logger.error(f"Unexpected error fetching initial price series for {symbols_to_process[0]} in {agent_name}: {e}", exc_info=True)
        return {
            "symbol": symbol_input,
            "verdict": "ERROR",
            "confidence": 0.0,
            "value": 0,
            "details": {"error": f"Unexpected error fetching initial price data: {e}"},
            "score": 0.0,
            "agent_name": agent_name,
            "error": f"Unexpected error fetching initial price data: {e}"
        }

    results = {}
    for sym_proc in symbols_to_process:
        try:
            # Corrected call: run_full_cycle expects a single symbol string.
            # It returns a dictionary of agent_name: agent_result.
            cycle_data_dict = await run_full_cycle(sym_proc)
            
            if cycle_data_dict and isinstance(cycle_data_dict, dict):
                if "error" in cycle_data_dict and cycle_data_dict.get("status") == "failed": # Check for top-level cycle error
                    logger.error(f"run_full_cycle for {sym_proc} in {agent_name} itself reported an error: {cycle_data_dict['error']}")
                    results[sym_proc] = {"verdict": "ERROR", "score": 0.0, "error": cycle_data_dict['error']}
                else:
                    # If no top-level error, cycle_data_dict contains individual agent results.
                    # Extract a summary verdict/score, e.g., from verdict_orchestrator_agent or composite_valuation_agent.
                    summary_verdict = "UNKNOWN"
                    summary_score = 0.0
                    # Prioritize verdict_orchestrator_agent if available and successful
                    verdict_orch_res = cycle_data_dict.get("verdict_orchestrator_agent")
                    if verdict_orch_res and verdict_orch_res.get("error") is None:
                        summary_verdict = verdict_orch_res.get("verdict", "UNKNOWN")
                        summary_score = verdict_orch_res.get("score", 0.0)
                    else: # Fallback to composite_valuation_agent or other key agent
                        comp_val_res = cycle_data_dict.get("composite_valuation_agent")
                        if comp_val_res and comp_val_res.get("error") is None:
                            summary_verdict = comp_val_res.get("verdict", "UNKNOWN")
                            summary_score = comp_val_res.get("score", 0.0)

                    results[sym_proc] = {
                        "verdict": summary_verdict,
                        "score": summary_score,
                        "error": None, # No error at this level, individual agents might have errors within cycle_data_dict
                        # "full_cycle_results": cycle_data_dict # Optionally store all results for debugging
                    }
            else:
                logger.error(f"run_full_cycle for {sym_proc} in {agent_name} returned unexpected data type: {type(cycle_data_dict)}")
                results[sym_proc] = {"verdict": "ERROR", "score": 0.0, "error": "Unexpected result type from sub-cycle"}
        except Exception as e:
            logger.error(f"Error in run_full_cycle for {sym_proc} within {agent_name}: {e}", exc_info=True)
            results[sym_proc] = {"verdict": "ERROR", "score": 0.0, "error": str(e)}

    scores = []
    for res_data in results.values():
        if res_data.get("error") is None and res_data.get("score") is not None:
            scores.append(res_data["score"])

    avg_score = sum(scores) / len(scores) if scores else 0.0
    buy_count = sum(
        1 for res_data in results.values() if res_data.get("verdict") in ("STRONG_BUY", "BUY") and res_data.get("error") is None
    )

    final_verdict = "NO_DATA"
    main_symbol_result_data = results.get(symbol_input)
    error_message = None

    if main_symbol_result_data:
        if main_symbol_result_data.get("error"):
            final_verdict = "ERROR"
            error_message = main_symbol_result_data.get("error")
        elif main_symbol_result_data.get("verdict"):
            final_verdict = main_symbol_result_data.get("verdict")
    
    result_payload = {
        "symbol": symbol_input,
        "verdict": final_verdict,
        "confidence": round(avg_score, 4),
        "value": len(symbols_to_process),
        "details": {
            "avg_score": avg_score,
            "buy_count": buy_count,
            "per_symbol": results,
        },
        "score": avg_score,
        "agent_name": agent_name,
    }
    if error_message:
        result_payload["error"] = error_message

    await redis_client.set(cache_key, json.dumps(result_payload), ex=settings.agent_cache_ttl) # Corrected access
    await tracker.update("automation", agent_name, "implemented")
    return result_payload
