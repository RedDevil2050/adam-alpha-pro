from backend.utils.data_provider import fetch_company_info # Use unified provider
from loguru import logger
from backend.agents.decorators import standard_agent_execution  # Import decorator

agent_name = "eps_agent"
AGENT_CATEGORY = "valuation"  # Define category for the decorator


@standard_agent_execution(
    agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=3600
)
async def run(symbol: str, agent_outputs: dict = None) -> dict:
    # Boilerplate handled by decorator

    # Fetch overview data which contains EPS using unified provider
    company_info = await fetch_company_info(symbol)

    if not company_info:
        return {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {"reason": "Could not fetch company info"},
            "agent_name": agent_name,
        }

    eps_str = company_info.get("EPS")
    eps = None

    if eps_str and eps_str.lower() not in ["none", "-", ""]:
        try:
            eps = float(eps_str)
        except (ValueError, TypeError):
            logger.warning(
                f"[{agent_name}] Could not parse EPS for {symbol}: {eps_str}"
            )
            return {
                "symbol": symbol,
                "verdict": "INVALID_DATA",
                "confidence": 0.1,
                "value": None,
                "details": {"raw_eps": eps_str, "reason": "Could not parse EPS value"},
                "agent_name": agent_name,
            }
    else:
        # Handle cases where EPS is explicitly None or missing
        logger.warning(
            f"[{agent_name}] EPS not available for {symbol} in overview data."
        )
        return {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.5,
            "value": None,  # Confidence 0.5 as we know it's missing
            "details": {
                "raw_eps": eps_str,
                "reason": "EPS value not provided or is None",
            },
            "agent_name": agent_name,
        }

    # EPS is successfully parsed
    # Determine verdict based on whether EPS is positive or negative
    if eps > 0:
        verdict = "POSITIVE_EPS"
        confidence = 0.95
    else:
        verdict = "NEGATIVE_EPS"
        confidence = 0.95  # High confidence in the sign

    # Create success result dictionary
    result = {
        "symbol": symbol,
        "verdict": verdict,
        "confidence": round(confidence, 4),
        "value": round(eps, 4),  # Return the EPS value
        "details": {"eps": round(eps, 4), "data_source": "alpha_vantage_overview"},
        "agent_name": agent_name,
    }

    return result
