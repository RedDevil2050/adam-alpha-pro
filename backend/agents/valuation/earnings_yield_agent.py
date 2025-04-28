import asyncio
from backend.utils.data_provider import fetch_price_point, fetch_eps, fetch_alpha_vantage # Added fetch_alpha_vantage
from loguru import logger
from backend.agents.decorators import standard_agent_execution # Import decorator

agent_name = "earnings_yield_agent"
AGENT_CATEGORY = "valuation" # Define category for the decorator

@standard_agent_execution(agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=3600)
async def run(symbol: str, agent_outputs: dict = None) -> dict:
    # Boilerplate handled by decorator

    current_price = None
    eps = None
    eps_source = "unknown"

    # 1. Fetch Price
    price_data_task = fetch_price_point(symbol)

    # 2. Determine EPS source and fetch if necessary
    eps_task = None
    if agent_outputs and "eps_agent" in agent_outputs and agent_outputs["eps_agent"].get("value") is not None:
        try:
            eps = float(agent_outputs["eps_agent"]["value"])
            eps_source = "eps_agent"
            logger.info(f"[{agent_name}] Using EPS from eps_agent for {symbol}")
        except (ValueError, TypeError):
            logger.warning(f"[{agent_name}] Could not parse EPS from eps_agent for {symbol}, falling back.")
            # Fallback: Fetch EPS directly or from overview
            eps_task = fetch_alpha_vantage("query", {"function": "OVERVIEW", "symbol": symbol})
            eps_source = "alpha_vantage_overview_fallback"
    else:
        # Fetch EPS from overview if not available from agent
        eps_task = fetch_alpha_vantage("query", {"function": "OVERVIEW", "symbol": symbol})
        eps_source = "alpha_vantage_overview"

    # 3. Gather results
    results = await asyncio.gather(price_data_task, eps_task, return_exceptions=True)

    price_data = results[0] if not isinstance(results[0], Exception) else None
    overview_data = results[1] if eps_task and not isinstance(results[1], Exception) else None

    # Extract price
    if price_data:
        current_price = price_data.get("latestPrice")

    # Extract EPS if fetched via fallback/direct
    if eps is None and overview_data:
        eps_str = overview_data.get("EPS")
        if eps_str and eps_str.lower() not in ["none", "-", ""]:
            try:
                eps = float(eps_str)
            except (ValueError, TypeError):
                logger.warning(f"[{agent_name}] Could not parse EPS from Alpha Vantage overview for {symbol}: {eps_str}")
        else:
             logger.warning(f"[{agent_name}] EPS not found in Alpha Vantage overview for {symbol}")

    # 4. Validate data
    if eps is None or eps <= 0 or current_price is None or current_price <= 0:
        # Allow for negative EPS, but yield calculation might be less meaningful
        if eps is None or current_price is None or current_price <= 0:
            details = {
                "current_price": current_price,
                "eps": eps,
                "eps_source": eps_source,
                "reason": f"Missing or invalid essential data (Price: {current_price}, EPS: {eps})"
            }
            return {
                "symbol": symbol, "verdict": "NO_DATA", "confidence": 0.0, "value": None,
                "details": details, "agent_name": agent_name
            }
        # If EPS is negative, proceed but note it
        logger.info(f"[{agent_name}] Proceeding with negative EPS for {symbol}: {eps}")

    # 5. Calculate Earnings Yield (Core Logic)
    earnings_yield = (eps / current_price) * 100

    # 6. Determine Verdict (using fixed thresholds, market regime logic removed)
    # Thresholds can be adjusted based on general market conditions or preferences
    high_threshold = 8.0 # e.g., > 8% is attractive
    low_threshold = 4.0  # e.g., < 4% is expensive

    if earnings_yield > high_threshold:
        verdict = "ATTRACTIVE"
        confidence = 0.8 # High yield suggests undervaluation
    elif earnings_yield > low_threshold:
        verdict = "FAIR_VALUE"
        confidence = 0.6
    elif earnings_yield > 0: # Positive but low yield
         verdict = "EXPENSIVE"
         confidence = 0.4
    else: # Negative earnings yield
         verdict = "NEGATIVE_EARNINGS"
         confidence = 0.5 # Confidence that earnings are negative

    # Create success result dictionary (Core Logic)
    result = {
        "symbol": symbol,
        "verdict": verdict,
        "confidence": round(confidence, 4),
        "value": round(earnings_yield, 2), # Report yield percentage
        "details": {
            "earnings_yield_percent": round(earnings_yield, 2),
            "current_price": round(current_price, 2),
            "eps": round(eps, 4),
            "eps_source": eps_source,
            # "market_regime": "NOT_IMPLEMENTED" # Market regime logic removed
        },
        "agent_name": agent_name
    }

    return result
