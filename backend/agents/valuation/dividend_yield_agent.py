import asyncio
from backend.utils.data_provider import (
    fetch_price_point,
    fetch_alpha_vantage,
)  # Use fetch_alpha_vantage
from loguru import logger
from backend.agents.decorators import standard_agent_execution  # Import decorator
from backend.config.settings import get_settings  # Added import

agent_name = "dividend_yield_agent"
AGENT_CATEGORY = "valuation"  # Define category for the decorator


@standard_agent_execution(
    agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=3600
)
async def run(symbol: str, agent_outputs: dict = {}) -> dict:
    """
    Calculates the Dividend Yield for a given stock symbol and assesses its attractiveness.

    Purpose:
        Determines the annual dividend payment relative to the stock's current market price.
        It helps income-focused investors assess the return generated from dividends.

    Metrics Calculated:
        - Dividend Yield (%) = (Annual Dividend per Share / Current Market Price per Share) * 100

    Logic:
        1. Attempts to retrieve dividend yield or dividend per share (DPS) from the output of `dividend_agent` if available in `agent_outputs`.
        2. If data is found in `agent_outputs`:
            - If yield is present, use it directly.
            - If only DPS is present, fetch the current price (`fetch_price_point`) and calculate the yield.
        3. If data is not found in `agent_outputs` or is insufficient:
            - Fetch company overview data (`fetch_alpha_vantage`) which contains DividendYield and DividendPerShare.
            - Fetch the current price (`fetch_price_point`).
            - Attempt to parse DividendYield and DividendPerShare from the overview.
            - If yield is missing but DPS and price are available, calculate the yield.
        4. Validates the calculated or fetched yield.
        5. If no valid yield can be determined, checks if the company explicitly pays no dividend (based on overview data if available) and returns 'NO_DIVIDEND' or 'NO_DATA'.
        6. Compares the dividend yield percentage against configurable thresholds (e.g., HIGH_YIELD > 5%, ATTRACTIVE_YIELD > 2.5%, MODERATE_YIELD > 1.0%):
            - Assigns verdicts: 'HIGH_YIELD', 'ATTRACTIVE_YIELD', 'MODERATE_YIELD', 'LOW_YIELD'.
        7. Sets a fixed confidence score based on the verdict category.

    Dependencies:
        - Optionally uses output from `dividend_agent`.
        - Requires current stock price (`fetch_price_point`).
        - Requires company overview data (`fetch_alpha_vantage`) for yield/DPS or fallback calculation.

    Configuration Used (from settings.py -> AgentSettings -> DividendYieldAgentSettings): # Updated docstring section
        - `THRESHOLD_HIGH`: Minimum yield % for 'HIGH_YIELD'.
        - `THRESHOLD_ATTRACTIVE`: Minimum yield % for 'ATTRACTIVE_YIELD'.
        - `THRESHOLD_MODERATE`: Minimum yield % for 'MODERATE_YIELD'.

    Return Structure:
        A dictionary containing:
        - symbol (str): The stock symbol.
        - verdict (str): 'HIGH_YIELD', 'ATTRACTIVE_YIELD', 'MODERATE_YIELD', 'LOW_YIELD', 'NO_DIVIDEND', or 'NO_DATA'.
        - confidence (float): A fixed score based on the verdict category (0.0 to 1.0).
        - value (float | None): The calculated dividend yield percentage, or None if not available.
        - details (dict): Contains yield %, price, DPS, data source, and configured thresholds.
        - agent_name (str): The name of this agent.
        - error (str | None): Error message if an issue occurred (handled by decorator).
    """
    # Fetch settings
    settings = get_settings()
    yield_settings = settings.agent_settings.dividend_yield

    dividend_yield = None
    current_price = None
    annual_dividend = None
    data_source = "unknown"

    # 1. Try to get data from dividend_agent output
    if agent_outputs and "dividend_agent" in agent_outputs:
        div_agent_data = agent_outputs["dividend_agent"]
        if div_agent_data.get("verdict") not in ["NO_DATA", "ERROR"]:
            details = div_agent_data.get("details", {})
            yield_pct = details.get("dividend_yield_percent")
            dps = details.get("dividend_per_share")
            if yield_pct is not None:
                dividend_yield = yield_pct / 100.0
                annual_dividend = dps  # DPS is often the annual amount in summaries
                # Need price to confirm yield calculation or if only DPS is available
                price_data = await fetch_price_point(symbol)
                current_price = price_data.get("latestPrice") if price_data else None
                data_source = "dividend_agent + price_point"
            elif dps is not None:
                # If only DPS is available from dividend_agent, fetch price to calculate yield
                price_data = await fetch_price_point(symbol)
                current_price = price_data.get("latestPrice") if price_data else None
                annual_dividend = dps
                if current_price and current_price > 0:
                    dividend_yield = annual_dividend / current_price
                    data_source = "dividend_agent (DPS) + price_point"
                else:
                    data_source = "dividend_agent (DPS only, no price)"

    # 2. If not available from dividend_agent, fetch data directly
    if dividend_yield is None and annual_dividend is None:
        data_source = "alpha_vantage + price_point"
        overview_task = fetch_alpha_vantage(
            "query", {"function": "OVERVIEW", "symbol": symbol}
        )
        price_task = fetch_price_point(symbol)
        overview_data, price_data = await asyncio.gather(overview_task, price_task)

        current_price = price_data.get("latestPrice") if price_data else None

        if overview_data:
            dividend_yield_str = overview_data.get("DividendYield")
            dividend_per_share_str = overview_data.get("DividendPerShare")

            try:
                if dividend_yield_str and dividend_yield_str.lower() not in [
                    "none",
                    "-",
                    "",
                ]:
                    dividend_yield = float(dividend_yield_str)
            except (ValueError, TypeError):
                logger.warning(
                    f"[{agent_name}] Could not parse DividendYield for {symbol}: {dividend_yield_str}"
                )

            try:
                if dividend_per_share_str and dividend_per_share_str.lower() not in [
                    "none",
                    "-",
                    "",
                ]:
                    annual_dividend = float(dividend_per_share_str)
            except (ValueError, TypeError):
                logger.warning(
                    f"[{agent_name}] Could not parse DividendPerShare for {symbol}: {dividend_per_share_str}"
                )

            # If yield is missing but DPS and price are available, calculate yield
            if (
                dividend_yield is None
                and annual_dividend is not None
                and current_price is not None
                and current_price > 0
            ):
                dividend_yield = annual_dividend / current_price
                logger.info(
                    f"[{agent_name}] Calculated yield from DPS and Price for {symbol}"
                )

    # 3. Validate data and determine verdict
    if dividend_yield is None or dividend_yield < 0:
        # Check if it explicitly pays no dividend based on overview data if fetched
        pays_dividends = False
        if data_source == "alpha_vantage + price_point" and overview_data:
            pays_dividends = annual_dividend is not None and annual_dividend > 0

        if not pays_dividends:
            verdict = "NO_DIVIDEND"
            confidence = 0.9
            value = 0.0
            details_reason = "No dividend data found or indicated zero dividend."
        else:
            # Data inconsistency or missing price/yield info
            verdict = "NO_DATA"
            confidence = 0.0
            value = None
            details_reason = f"Could not determine dividend yield (Yield: {dividend_yield}, Price: {current_price}, DPS: {annual_dividend})"

        return {
            "symbol": symbol,
            "verdict": verdict,
            "confidence": confidence,
            "value": value,
            "details": {
                "reason": details_reason,
                "data_source": data_source,
                "current_price": current_price,
                "annual_dividend": annual_dividend,
            },
            "agent_name": agent_name,
        }

    # Calculate yield percentage
    dividend_yield_percent = dividend_yield * 100

    # Score based on dividend yield ranges (Core Logic)
    if dividend_yield_percent > yield_settings.THRESHOLD_HIGH:  # Use setting
        verdict = "HIGH_YIELD"
        confidence = 0.8
    elif dividend_yield_percent > yield_settings.THRESHOLD_ATTRACTIVE:  # Use setting
        verdict = "ATTRACTIVE_YIELD"
        confidence = 0.7
    elif dividend_yield_percent > yield_settings.THRESHOLD_MODERATE:  # Use setting
        verdict = "MODERATE_YIELD"
        confidence = 0.5
    else:
        verdict = "LOW_YIELD"
        confidence = 0.4

    # Create success result dictionary (Core Logic)
    result = {
        "symbol": symbol,
        "verdict": verdict,
        "confidence": round(confidence, 4),
        "value": round(dividend_yield_percent, 2),  # Report yield percentage
        "details": {
            "yield_percent": round(dividend_yield_percent, 2),
            "current_price": (
                round(current_price, 2) if current_price is not None else None
            ),
            "annual_dividend_per_share": (
                round(annual_dividend, 4) if annual_dividend is not None else None
            ),
            "data_source": data_source,
            "threshold_high": yield_settings.THRESHOLD_HIGH,  # Use setting
            "threshold_attractive": yield_settings.THRESHOLD_ATTRACTIVE,  # Use setting
            "threshold_moderate": yield_settings.THRESHOLD_MODERATE,  # Use setting
        },
        "agent_name": agent_name,
    }

    return result
