import asyncio
# Import the run functions directly from the refactored agents
from backend.agents.valuation.dcf_agent import run as dcf_run
from backend.agents.valuation.pe_ratio_agent import run as pe_run
from backend.agents.valuation.pb_ratio_agent import run as pb_run # Assuming pb_ratio_agent is also refactored
from loguru import logger
from backend.agents.decorators import standard_agent_execution # Import decorator

agent_name = "intrinsic_composite_agent"
AGENT_CATEGORY = "valuation" # Define category for the decorator

# Weights for each component (can be adjusted)
WEIGHTS = {
    "dcf": 0.4,
    "pe": 0.3,
    "pb": 0.3
}

# Mapping from sub-agent verdicts to a numerical score (-1 to 1)
VERDICT_SCORES = {
    # DCF Agent Verdicts (Example - adjust based on actual dcf_agent verdicts)
    "UNDERVALUED": 1.0,
    "FAIR_VALUE": 0.0,
    "OVERVALUED": -1.0,
    # PE Ratio Agent Verdicts (Example - adjust based on actual pe_ratio_agent verdicts)
    "LOW_PE": 1.0, # Assuming low PE is good
    "MODERATE_PE": 0.0,
    "HIGH_PE": -1.0,
    # PB Ratio Agent Verdicts (Example - adjust based on actual pb_ratio_agent verdicts)
    "LOW_PB": 1.0, # Assuming low PB is good
    "MODERATE_PB": 0.0,
    "HIGH_PB": -1.0,
    # Add other potential verdicts from sub-agents if necessary
}

@standard_agent_execution(agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=1800) # Shorter TTL as it depends on others
async def run(symbol: str, agent_outputs: dict = None) -> dict:
    # Boilerplate handled by decorator

    # Run dependent agents concurrently
    # Pass agent_outputs down in case they can reuse data
    tasks = {
        "dcf": dcf_run(symbol, agent_outputs),
        "pe": pe_run(symbol, agent_outputs),
        "pb": pb_run(symbol, agent_outputs)
    }
    results = await asyncio.gather(*tasks.values(), return_exceptions=True)

    sub_agent_results = {}
    valid_scores = []
    weighted_score_sum = 0.0
    total_weight = 0.0

    # Process results
    for i, agent_key in enumerate(tasks.keys()):
        result = results[i]
        sub_agent_results[agent_key] = result # Store raw result for details

        if isinstance(result, Exception):
            logger.warning(f"[{agent_name}] Sub-agent {agent_key} failed for {symbol}: {result}")
            continue # Skip failed agents

        if result.get("verdict") in ["ERROR", "NO_DATA", "INVALID_DATA", None]:
            logger.warning(f"[{agent_name}] Sub-agent {agent_key} returned invalid verdict for {symbol}: {result.get('verdict')}")
            continue # Skip agents with no usable verdict

        verdict = result.get("verdict")
        confidence = result.get("confidence", 0.0)
        value_score = VERDICT_SCORES.get(verdict, 0.0) # Get numerical score for the verdict

        # Calculate weighted score: score * confidence * weight
        component_score = value_score * confidence * WEIGHTS[agent_key]
        weighted_score_sum += component_score
        total_weight += WEIGHTS[agent_key]
        valid_scores.append({
            "agent": agent_key,
            "verdict": verdict,
            "confidence": confidence,
            "value_score": value_score,
            "weight": WEIGHTS[agent_key],
            "component_score": component_score
        })

    # Check if any valid scores were obtained
    if total_weight == 0:
        logger.warning(f"[{agent_name}] No valid valuation signals found for {symbol}")
        return {
            "symbol": symbol, "verdict": "NO_DATA", "confidence": 0.0, "value": None,
            "details": {"reason": "No valid underlying valuation signals", "sub_agent_results": sub_agent_results},
            "agent_name": agent_name
        }

    # Calculate final composite score (normalized by total weight used)
    composite_score = weighted_score_sum / total_weight # Score range: -1 to 1

    # Determine final verdict based on composite score
    if composite_score > 0.5:
        verdict = "STRONG_UNDERVALUATION"
        confidence = min(1.0, composite_score) # Confidence related to score strength
    elif composite_score > 0.1:
        verdict = "MODERATE_UNDERVALUATION"
        confidence = min(1.0, composite_score * 1.5) # Scale confidence
    elif composite_score > -0.1:
        verdict = "FAIR_VALUE"
        confidence = 0.5 # Lower confidence around fair value
    elif composite_score > -0.5:
        verdict = "MODERATE_OVERVALUATION"
        confidence = min(1.0, abs(composite_score * 1.5))
    else:
        verdict = "STRONG_OVERVALUATION"
        confidence = min(1.0, abs(composite_score))

    # Create success result dictionary
    result = {
        "symbol": symbol,
        "verdict": verdict,
        "confidence": round(confidence, 4),
        "value": round(composite_score, 4), # Composite score as the value
        "details": {
            "composite_score": round(composite_score, 4),
            "calculation_breakdown": valid_scores,
            "sub_agent_raw_results": sub_agent_results # Include raw results for transparency
        },
        "agent_name": agent_name
    }

    return result
