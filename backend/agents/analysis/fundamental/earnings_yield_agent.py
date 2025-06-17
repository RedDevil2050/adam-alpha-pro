import asyncio
from backend.utils.data_provider import fetch_company_info, fetch_price_point # Use unified provider
from loguru import logger
from backend.agents.decorators import standard_agent_execution  # Import decorator

agent_name = "earnings_yield_agent"
AGENT_CATEGORY = "valuation"  # Define category for the decorator


@standard_agent_execution(
    agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=3600
)
async def run(symbol: str, agent_outputs: dict = None) -> dict:
    # Boilerplate handled by decorator

    # Fetch necessary data using unified provider
    company_info_task = fetch_company_info(symbol)
    price_data_task = fetch_price_point(symbol)
    company_info, price_data = await asyncio.gather(company_info_task, price_data_task)

    if not company_info or not price_data or "error" in price_data:
        reason = "Could not fetch required data (company info or price)."
        if price_data and "error" in price_data:
            reason += f" Price fetch error: {price_data['error']}"
        logger.warning(f"[{agent_name}] {reason} for {symbol}")
        return {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {"reason": reason},
            "agent_name": agent_name,
        }

    eps_str = company_info.get("EPS")
    current_price = price_data.get("price") # Assuming fetch_price_point returns {'price': ...}

    if current_price is None:
         logger.warning(f"[{agent_name}] Current price not available for {symbol}")
         return {
             "symbol": symbol,
             "verdict": "NO_DATA",
             "confidence": 0.0,
             "value": None,
             "details": {"reason": "Current price not available"},
             "agent_name": agent_name,
         }

    eps = None
    eps_source = "unknown"

    # Extract EPS if available
    if eps_str and eps_str.lower() not in ["none", "-", ""]:
        try:
            eps = float(eps_str)
            eps_source = "company_info"
        except (ValueError, TypeError):
            logger.warning(
                f"[{agent_name}] Could not parse EPS from company info for {symbol}: {eps_str}"
            )
    else:
        logger.warning(
            f"[{agent_name}] EPS not found in company info for {symbol}"
        )

    # 4. Validate data
    if eps is None or eps <= 0 or current_price is None or current_price <= 0:
        # Allow for negative EPS, but yield calculation might be less meaningful
        if eps is None or current_price is None or current_price <= 0:
            details = {
                "current_price": current_price,
                "eps": eps,
                "eps_source": eps_source,
                "reason": f"Missing or invalid essential data (Price: {current_price}, EPS: {eps})",
            }
            return {
                "symbol": symbol,
                "verdict": "NO_DATA",
                "confidence": 0.0,
                "value": None,
                "details": details,
                "agent_name": agent_name,
            }
        # If EPS is negative, proceed but note it
        logger.info(f"[{agent_name}] Proceeding with negative EPS for {symbol}: {eps}")

    # Ensure eps and current_price are floats before division
    try:
        eps = float(eps_str)
        current_price = float(current_price) # Ensure price is float
        if current_price <= 0:
             raise ValueError("Price must be positive")
    except (ValueError, TypeError, AttributeError):
        logger.warning(
            f"[{agent_name}] Could not parse EPS ('{eps_str}') or price ('{current_price}') for {symbol}"
        )
        return {
            "symbol": symbol,
            "verdict": "INVALID_DATA",
            "confidence": 0.1,
            "value": None,
            "details": {"raw_eps": eps_str, "raw_price": current_price, "reason": "Could not parse EPS or price"},
            "agent_name": agent_name,
        }

    if eps is None: # Handle case where EPS parsing failed earlier but wasn't caught (shouldn't happen with above logic, but good practice)
         logger.warning(f"[{agent_name}] EPS is None after parsing for {symbol}")
         return {
             "symbol": symbol,
             "verdict": "INVALID_DATA",
             "confidence": 0.1,
             "value": None,
             "details": {"reason": "EPS became None unexpectedly"},
             "agent_name": agent_name,
         }


    # Calculate Earnings Yield using the already fetched and validated eps and current_price
    # Note: Redundant fetches for price_data and eps_data were removed here.
    earnings_yield = (eps / current_price) * 100 if current_price else 0

    # Determine verdict based on yield (example thresholds)
    # Thresholds can be adjusted based on general market conditions or preferences
    high_threshold = 8.0  # e.g., > 8% is attractive
    low_threshold = 4.0  # e.g., < 4% is expensive

    if earnings_yield > high_threshold:
        verdict = "ATTRACTIVE"
        confidence = 0.8  # High yield suggests undervaluation
    elif earnings_yield > low_threshold:
        verdict = "FAIR_VALUE"
        confidence = 0.6
    elif earnings_yield > 0:  # Positive but low yield
        verdict = "EXPENSIVE"
        confidence = 0.4
    else:  # Negative earnings yield
        verdict = "NEGATIVE_EARNINGS"
        confidence = 0.5  # Confidence that earnings are negative

    # Create success result dictionary (Core Logic)
    result = {
        "symbol": symbol,
        "verdict": verdict,
        "confidence": round(confidence, 4),
        "value": round(earnings_yield, 2),  # Report yield percentage
        "details": {
            "earnings_yield_percent": round(earnings_yield, 2),
            "current_price": round(current_price, 2),
            "eps": round(eps, 4),
            "eps_source": eps_source,
        },
        "agent_name": agent_name,
    }

    return result
