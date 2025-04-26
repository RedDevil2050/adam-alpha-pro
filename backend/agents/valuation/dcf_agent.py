
from backend.config.settings import settings
from backend.utils.data_provider import fetch_price_point, fetch_alpha_vantage
from loguru import logger

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

        growth_rate = settings.DCF_DEFAULT_GROWTH_RATE
        discount_rate = settings.DCF_DEFAULT_DISCOUNT_RATE
        terminal_pe = settings.DCF_DEFAULT_TERMINAL_PE
        years = settings.DCF_YEARS

        projected_eps = [eps * ((1 + growth_rate) ** year) for year in range(1, years + 1)]
        present_values = [eps_val / ((1 + discount_rate) ** idx) for idx, eps_val in enumerate(projected_eps, start=1)]
        terminal_value = (projected_eps[-1] * terminal_pe) / ((1 + discount_rate) ** years)

        intrinsic_value = sum(present_values) + terminal_value
        confidence = 100.0 * (intrinsic_value - current_price) / current_price

        if confidence > 30:
            verdict = "BUY"
        elif confidence > 0:
            verdict = "HOLD"
        else:
            verdict = "AVOID"

        return {
            "symbol": symbol,
            "verdict": verdict,
            "confidence": min(max(confidence, 0), 100.0),
            "value": intrinsic_value,
            "details": {
                "current_price": current_price,
                "base_eps": eps,
                "growth_rate": growth_rate,
                "discount_rate": discount_rate,
                "terminal_pe": terminal_pe,
                "years": years
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
