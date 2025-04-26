from backend.config.settings import settings
from backend.utils.data_provider import fetch_price_point, fetch_alpha_vantage
from loguru import logger
import numpy as np

agent_name = "dcf_agent"

async def run(symbol: str, agent_outputs: dict) -> dict:
    try:
        price_data = await fetch_price_point(symbol)
        current_price = price_data.get("latestPrice", 0)

        eps = None
        if "eps_agent" in agent_outputs and agent_outputs["eps_agent"].get("value"):
            eps = float(agent_outputs["eps_agent"]["value"])
        else:
            overview_data = await fetch_alpha_vantage("query", {"function": "OVERVIEW", "symbol": symbol})
            eps_str = overview_data.get("EPS")
            if eps_str and eps_str.lower() != "none":
                eps = float(eps_str)

        if not eps or eps <= 0 or not current_price or current_price <= 0:
            return {
                "symbol": symbol,
                "verdict": "NO_DATA",
                "confidence": 0.0,
                "value": None,
                "details": {
                    "current_price": current_price,
                    "base_eps": eps
                },
                "error": "Missing or invalid EPS/Price data",
                "agent_name": agent_name
            }

        # Enhanced multi-stage growth calculation
        growth_stages = [
            settings.DCF_GROWTH_STAGE1 or 0.15,  # High growth (1-5 years)
            settings.DCF_GROWTH_STAGE2 or 0.10,  # Medium growth (6-10 years)
            settings.DCF_GROWTH_STAGE3 or 0.04   # Terminal growth
        ]
        
        # Risk-adjusted discount rate based on beta
        beta = float(overview_data.get("Beta", 1.0))
        risk_free_rate = settings.RISK_FREE_RATE or 0.04
        market_premium = settings.MARKET_RISK_PREMIUM or 0.06
        discount_rate = risk_free_rate + beta * market_premium

        # Monte Carlo simulation parameters
        n_simulations = 1000
        simulation_results = []
        
        for _ in range(n_simulations):
            # Randomize growth rates with normal distribution
            perturbed_growth = [
                np.random.normal(g, 0.02) for g in growth_stages
            ]
            
            # Perturb discount rate
            perturbed_discount = np.random.normal(discount_rate, 0.01)
            
            # Run DCF with perturbed parameters
            sim_value = simulate_dcf(eps, perturbed_growth, perturbed_discount)
            simulation_results.append(sim_value)
        
        # Statistical analysis of simulations
        mean_value = np.mean(simulation_results)
        std_dev = np.std(simulation_results)
        percentile_5 = np.percentile(simulation_results, 5)
        percentile_95 = np.percentile(simulation_results, 95)
        
        # Use mean value as intrinsic value
        intrinsic_value = mean_value
        margin_of_safety = (intrinsic_value - current_price) / current_price * 100

        if margin_of_safety > 30:
            verdict = "STRONG_BUY"
            confidence = 90.0
        elif margin_of_safety > 15:
            verdict = "BUY"
            confidence = 70.0
        elif margin_of_safety > 0:
            verdict = "HOLD"
            confidence = 50.0
        else:
            verdict = "AVOID"
            confidence = max(0, 50 + margin_of_safety)

        return {
            "symbol": symbol,
            "verdict": verdict,
            "confidence": confidence,
            "value": round(intrinsic_value, 2),
            "details": {
                "current_price": current_price,
                "margin_of_safety": round(margin_of_safety, 2),
                "simulation_stats": {
                    "mean": round(mean_value, 2),
                    "std_dev": round(std_dev, 2),
                    "confidence_interval": [round(percentile_5, 2), round(percentile_95, 2)]
                },
                "discount_rate": round(discount_rate * 100, 2),
                "growth_stages": growth_stages,
                "beta": beta
            },
            "error": None,
            "agent_name": agent_name
        }

    except Exception as e:
        logger.error(f"DCF error for {symbol}: {e}")
        return {
            "symbol": symbol,
            "verdict": "ERROR",
            "confidence": 0.0,
            "value": None,
            "details": {},
            "error": str(e),
            "agent_name": agent_name
        }

def simulate_dcf(base_eps: float, growth_rates: list, discount_rate: float) -> float:
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
        
    # Terminal value
    terminal_eps = current_eps * (1 + growth_rates[2])
    terminal_value = terminal_eps * settings.DCF_DEFAULT_TERMINAL_PE / (discount_rate - growth_rates[2])
    
    # Present values
    present_values = [eps / ((1 + discount_rate) ** (i+1)) for i, eps in enumerate(projected_eps)]
    terminal_pv = terminal_value / ((1 + discount_rate) ** len(projected_eps))
    
    return sum(present_values) + terminal_pv
