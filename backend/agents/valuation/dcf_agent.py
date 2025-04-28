import asyncio # Import asyncio
from backend.config.settings import get_settings # Use get_settings
from backend.utils.data_provider import fetch_price_point, fetch_alpha_vantage
from loguru import logger
import numpy as np
from backend.agents.decorators import standard_agent_execution # Import decorator

agent_name = "dcf_agent"
AGENT_CATEGORY = "valuation" # Define category for the decorator

# Helper function remains the same, but ensure it uses settings correctly if needed
def simulate_dcf(base_eps: float, growth_rates: list, discount_rate: float, terminal_pe: float) -> float:
    """Helper function for DCF Monte Carlo simulation"""
    projected_eps = []
    current_eps = base_eps

    # Stage 1 & 2
    for i in range(5):
        current_eps *= (1 + growth_rates[0])
        projected_eps.append(current_eps)
    for i in range(5):
        current_eps *= (1 + growth_rates[1])
        projected_eps.append(current_eps)

    # Terminal value calculation needs to handle potential zero or negative denominator
    terminal_growth_rate = growth_rates[2]
    if discount_rate <= terminal_growth_rate:
        # Handle case where discount rate is not sufficiently above terminal growth
        # Return NaN or raise an error, or use a very high PE as approximation
        # For now, let's return NaN to indicate an issue in this simulation run
        return np.nan

    terminal_eps = current_eps * (1 + terminal_growth_rate)
    terminal_value = terminal_eps * terminal_pe / (discount_rate - terminal_growth_rate)

    # Present values
    present_values = [eps / ((1 + discount_rate) ** (i+1)) for i, eps in enumerate(projected_eps)]
    terminal_pv = terminal_value / ((1 + discount_rate) ** len(projected_eps))

    return sum(present_values) + terminal_pv

@standard_agent_execution(agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=3600)
async def run(symbol: str, agent_outputs: dict = None) -> dict: # Added agent_outputs default
    # Boilerplate (cache check, try/except, cache set, tracker, error handling) is handled by decorator
    settings = get_settings()

    # Fetch required data concurrently (Core Logic)
    price_data_task = fetch_price_point(symbol)
    overview_data_task = fetch_alpha_vantage("query", {"function": "OVERVIEW", "symbol": symbol})
    price_data, overview_data = await asyncio.gather(price_data_task, overview_data_task)

    current_price = price_data.get("latestPrice") if price_data else None

    # Get EPS (Core Logic) - Prefer agent_outputs if available
    eps = None
    eps_source = "unknown"
    if agent_outputs and "eps_agent" in agent_outputs and agent_outputs["eps_agent"].get("value") is not None:
        try:
            eps = float(agent_outputs["eps_agent"]["value"])
            eps_source = "eps_agent"
        except (ValueError, TypeError):
            logger.warning(f"Could not parse EPS from eps_agent for {symbol}")

    if eps is None and overview_data:
        eps_str = overview_data.get("EPS")
        if eps_str and eps_str.lower() not in ["none", "-", ""]:
            try:
                eps = float(eps_str)
                eps_source = "alpha_vantage_overview"
            except (ValueError, TypeError):
                logger.warning(f"Could not parse EPS from Alpha Vantage overview for {symbol}: {eps_str}")

    # Get Beta (Core Logic)
    beta = 1.0 # Default beta
    beta_source = "default"
    if overview_data:
        beta_str = overview_data.get("Beta")
        if beta_str and beta_str.lower() not in ["none", "-", ""]:
            try:
                beta = float(beta_str)
                beta_source = "alpha_vantage_overview"
            except (ValueError, TypeError):
                 logger.warning(f"Could not parse Beta from Alpha Vantage overview for {symbol}: {beta_str}")

    # Validate essential data (Core Logic)
    if eps is None or eps <= 0 or current_price is None or current_price <= 0:
        details = {
            "current_price": current_price,
            "base_eps": eps,
            "eps_source": eps_source,
            "beta": beta,
            "beta_source": beta_source,
            "reason": f"Missing or invalid essential data (EPS: {eps}, Price: {current_price})"
        }
        return {
            "symbol": symbol, "verdict": "NO_DATA", "confidence": 0.0, "value": None,
            "details": details, "agent_name": agent_name
        }

    # DCF Parameters (Core Logic)
    growth_stages = [
        settings.valuation.DCF_GROWTH_STAGE1, # High growth (1-5 years)
        settings.valuation.DCF_GROWTH_STAGE2, # Medium growth (6-10 years)
        settings.valuation.DCF_GROWTH_STAGE3  # Terminal growth
    ]
    risk_free_rate = settings.data_provider.RISK_FREE_RATE
    market_premium = settings.valuation.MARKET_RISK_PREMIUM
    discount_rate = risk_free_rate + beta * market_premium
    terminal_pe = settings.valuation.DCF_DEFAULT_TERMINAL_PE

    # Monte Carlo Simulation (Core Logic)
    n_simulations = 1000 # Keep number of simulations reasonable
    simulation_results = []

    for _ in range(n_simulations):
        # Randomize growth rates and discount rate
        # Use truncated normal or ensure rates are reasonable (e.g., growth < discount)
        perturbed_growth = [
            max(0, np.random.normal(g, 0.02)) for g in growth_stages # Ensure non-negative growth
        ]
        perturbed_discount = max(0.01, np.random.normal(discount_rate, 0.01)) # Ensure positive discount rate

        # Run DCF simulation
        sim_value = simulate_dcf(eps, perturbed_growth, perturbed_discount, terminal_pe)
        if not np.isnan(sim_value): # Exclude invalid simulation runs
            simulation_results.append(sim_value)

    if not simulation_results:
        return {
            "symbol": symbol, "verdict": "ERROR", "confidence": 0.0, "value": None,
            "details": {"reason": "All DCF simulations resulted in invalid values (e.g., discount rate <= terminal growth)"},
            "agent_name": agent_name
        }

    # Statistical analysis (Core Logic)
    mean_value = np.mean(simulation_results)
    std_dev = np.std(simulation_results)
    percentile_5 = np.percentile(simulation_results, 5)
    percentile_95 = np.percentile(simulation_results, 95)

    # Verdict based on mean intrinsic value (Core Logic)
    intrinsic_value = mean_value
    margin_of_safety = (intrinsic_value - current_price) / current_price * 100 if current_price > 0 else np.inf

    # Confidence based on margin of safety and simulation std dev (relative to mean)
    relative_std_dev = std_dev / mean_value if mean_value != 0 else np.inf
    base_confidence = 0.0
    if margin_of_safety > 30: verdict = "STRONG_BUY"; base_confidence = 0.9
    elif margin_of_safety > 10: verdict = "BUY"; base_confidence = 0.7
    elif margin_of_safety > -10: verdict = "HOLD"; base_confidence = 0.5
    else: verdict = "AVOID"; base_confidence = 0.3

    # Adjust confidence based on simulation uncertainty
    uncertainty_penalty = min(1.0, relative_std_dev * 2) # Higher relative std dev reduces confidence
    final_confidence = base_confidence * (1 - uncertainty_penalty * 0.5) # Penalize up to 50%
    final_confidence = round(max(0.1, min(0.9, final_confidence)), 4) # Clamp confidence

    # Create success result dictionary (Core Logic)
    result = {
        "symbol": symbol,
        "verdict": verdict,
        "confidence": final_confidence,
        "value": round(intrinsic_value, 2),
        "details": {
            "current_price": round(current_price, 2),
            "intrinsic_value_mean": round(mean_value, 2),
            "margin_of_safety_percent": round(margin_of_safety, 2),
            "simulation_summary": {
                "count": len(simulation_results),
                "std_dev": round(std_dev, 2),
                "relative_std_dev": round(relative_std_dev, 4) if mean_value != 0 else None,
                "5th_percentile": round(percentile_5, 2),
                "95th_percentile": round(percentile_95, 2)
            },
            "inputs": {
                 "base_eps": round(eps, 4),
                 "eps_source": eps_source,
                 "beta": round(beta, 3),
                 "beta_source": beta_source,
                 "discount_rate_avg": round(discount_rate * 100, 2),
                 "growth_stages_avg": [round(g * 100, 1) for g in growth_stages],
                 "terminal_pe": terminal_pe
            }
        },
        "agent_name": agent_name
    }

    # Decorator handles caching and tracker update
    return result
