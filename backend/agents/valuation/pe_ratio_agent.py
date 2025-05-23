import asyncio
import pandas as pd
import numpy as np
from backend.utils.data_provider import (
    fetch_price_point,
    fetch_latest_eps,  # Corrected import
    fetch_historical_price_series,
)  # Updated imports
from loguru import logger
from backend.agents.decorators import standard_agent_execution
from backend.config.settings import get_settings
from datetime import datetime, timedelta

agent_name = "pe_ratio_agent"
AGENT_CATEGORY = "valuation"  # Define category for the decorator


@standard_agent_execution(
    agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=3600
)
async def run(symbol: str, agent_outputs: dict = None) -> dict:
    """
    Calculates the Price-to-Earnings (P/E) ratio for a given stock symbol and assesses its valuation
    relative to its historical P/E range.

    Purpose:
        Determines the current P/E ratio and compares it to the stock's historical P/E distribution
        to assess if it's currently undervalued, fairly valued, or overvalued relative to its own past.

    Metrics Calculated:
        - Current P/E Ratio (Current Price / Latest EPS)
        - Historical Mean P/E Ratio (over a configured period)
        - Historical Standard Deviation of P/E Ratio
        - Percentile Rank of Current P/E within its historical distribution
        - Z-Score of Current P/E relative to its historical mean and standard deviation

    Logic:
        1. Fetches current price, latest EPS, and historical price series concurrently.
        2. Validates fetched data (price > 0, EPS available and > 0). Returns 'NO_DATA' or 'NEGATIVE_EARNINGS' if validation fails.
        3. Calculates the current P/E ratio.
        4. If historical price data is available:
           a. Calculates a historical P/E series using historical prices and the *current* EPS (simplification).
           b. Calculates the mean and standard deviation of the historical P/E series.
           c. Calculates the percentile rank of the current P/E within the historical distribution.
           d. Calculates the Z-score of the current P/E.
        5. Determines a verdict based on the percentile rank compared to configured thresholds:
           - 'UNDERVALUED_REL_HIST' if percentile <= lower threshold.
           - 'OVERVALUED_REL_HIST' if percentile >= upper threshold.
           - 'FAIRLY_VALUED_REL_HIST' otherwise.
           - 'NO_HISTORICAL_CONTEXT' if historical analysis could not be performed.
        6. Calculates a dynamic confidence score based on the percentile rank (higher confidence for extreme percentiles).
        7. Returns the results including the current P/E, verdict, confidence, and detailed historical metrics.

    Dependencies:
        - Requires current stock price (`fetch_price_point`).
        - Requires latest Earnings Per Share (EPS) (`fetch_latest_eps`).
        - Requires historical price series (`fetch_historical_price_series`).

    Configuration Used (from settings.py):
        - `agent_settings.pe_ratio.HISTORICAL_YEARS`: Number of years for historical price data.
        - `agent_settings.pe_ratio.PERCENTILE_UNDERVALUED`: Percentile threshold below which P/E is considered undervalued relative to history.
        - `agent_settings.pe_ratio.PERCENTILE_OVERVALUED`: Percentile threshold above which P/E is considered overvalued relative to history.

    Return Structure:
        A dictionary containing:
        - symbol (str): The stock symbol.
        - verdict (str): Valuation verdict relative to history.
        - confidence (float): Dynamic confidence score (0.0 to 1.0).
        - value (float | None): The current P/E ratio.
        - details (dict): Contains current P/E, EPS, price, historical stats (mean, std dev, percentile, z-score), data source, and config used.
        - agent_name (str): The name of this agent.
        - error (str | None): Error message if an issue occurred (handled by decorator).
    """
    # Fetch settings
    settings = get_settings()
    pe_settings = settings.agent_settings.pe_ratio

    # Fetch current price, latest EPS, and historical prices concurrently
    try:
        price_task = fetch_price_point(symbol)
        eps_task = fetch_latest_eps(symbol)  # Corrected call
        
        # Convert years to start_date and end_date
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=pe_settings.HISTORICAL_YEARS * 365)).strftime("%Y-%m-%d")
        
        hist_price_task = fetch_historical_price_series(
            symbol, start_date=start_date, end_date=end_date
        )
        price_data, current_eps_data, historical_prices = await asyncio.gather(  # Renamed variable
            price_task, eps_task, hist_price_task
        )
    except Exception as fetch_err:
        logger.error(f"[{agent_name}] Error fetching data for {symbol}: {fetch_err}")
        return {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {"reason": f"Failed to fetch required data: {fetch_err}"},
            "agent_name": agent_name,
            "error": "Could not fetch required data (EPS, price, or sector PE)."
        }

    # Corrected parsing for raw Alpha Vantage JSON responses
    # price_data is the result of fetch_price_point -> fetch_quote -> fetch_data_resilient(symbol, "price")
    # The "data" part of fetch_data_resilient's result for Alpha Vantage (if successful) is {"price": value}
    # Accommodate "latestPrice" as well, as it might be provided by some sources or tests.
    parsed_price = None
    if price_data and isinstance(price_data, dict):
        price_value_candidate = None
        key_used_for_price = None

        if "price" in price_data:
            price_value_candidate = price_data.get("price")
            key_used_for_price = "price"
        elif "latestPrice" in price_data: # Check for "latestPrice" if "price" is not found
            price_value_candidate = price_data.get("latestPrice")
            key_used_for_price = "latestPrice"
            logger.info(f"[{agent_name}] Used 'latestPrice' key for price for {symbol} as 'price' key was not found.")

        if price_value_candidate is not None:
            try:
                parsed_price = float(price_value_candidate)
            except (ValueError, TypeError) as e:
                logger.warning(f"[{agent_name}] Error parsing price for {symbol} from key '{key_used_for_price}' with value '{price_value_candidate}': {e}")
        elif key_used_for_price: # A relevant key was found, but its value was None
            logger.warning(f"[{agent_name}] Price value is None for {symbol} from data_provider using key '{key_used_for_price}'.")
        else: # Neither "price" nor "latestPrice" key was found
            logger.warning(f"[{agent_name}] Neither 'price' nor 'latestPrice' key found in price_data for {symbol}. Price data: {str(price_data)[:200]}")
    current_price = parsed_price

    parsed_eps = None
    # current_eps_data is the result of fetch_latest_eps -> fetch_company_info(symbol, "eps")
    # fetch_company_info for "eps" returns a dict like {"eps": value}
    if current_eps_data and isinstance(current_eps_data, dict) and "eps" in current_eps_data: # Check for "eps" (lowercase)
        try:
            eps_val = current_eps_data["eps"]
            if eps_val is not None:
                parsed_eps = float(eps_val)
            else:
                logger.warning(f"[{agent_name}] EPS value is None for {symbol} from data_provider.")
        except (ValueError, TypeError) as e:
            logger.warning(f"[{agent_name}] Error parsing EPS for {symbol} from {current_eps_data['eps']}: {e}")
    current_eps = parsed_eps

    # Validate fetched data
    if current_price is None or current_price <= 0:
        return {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {"reason": f"Missing or invalid current price: {current_price}"},
            "agent_name": agent_name,
            "error": "Could not fetch required data (EPS, price, or sector PE)."
        }
    if current_eps is None:
        return {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {"reason": "Missing EPS data"},
            "agent_name": agent_name,
            "error": "Could not fetch required data (EPS, price, or sector PE)."
        }
    if current_eps <= 0:
        return {
            "symbol": symbol,
            "verdict": "NEGATIVE_EARNINGS",
            "confidence": 0.7,
            "value": None,
            "details": {
                "current_eps": current_eps,
                "reason": "EPS is zero or negative",
            },
            "agent_name": agent_name,
            "error": "Could not fetch required data (EPS, price, or sector PE)."
        }

    # Calculate Current P/E Ratio
    current_pe = current_price / current_eps

    # Calculate Historical P/E Analysis
    historical_pe_series = None
    mean_hist_pe = None
    std_hist_pe = None
    percentile_rank = None
    z_score = None
    data_source = "calculated_fundamental"

    # First, check if historical_prices exists
    if historical_prices is not None:
        # Ensure historical_prices is a pandas Series
        if not isinstance(historical_prices, pd.Series):
            try:
                # Attempt conversion assuming dict {date: price} or similar list
                historical_prices = pd.Series(historical_prices)
                # If index is not datetime-like, conversion might fail or be meaningless for time series
                # We might need more robust handling depending on expected list format
                if not pd.api.types.is_datetime64_any_dtype(historical_prices.index):
                     # Attempt to infer datetime index if it looks like dates, otherwise use default numeric
                     try:
                         historical_prices.index = pd.to_datetime(historical_prices.index)
                     except (ValueError, TypeError):
                         logger.warning(f"[{agent_name}] Could not infer datetime index for {symbol}, using default index.")
            except Exception as conversion_err:
                logger.warning(
                    f"[{agent_name}] Could not convert historical_prices to Series for {symbol}: {conversion_err}"
                )
                historical_prices = None  # Invalidate if conversion fails

        # Now check if conversion was successful and series is not empty
        if historical_prices is not None and not historical_prices.empty:
            # Calculate historical P/E using historical prices and CURRENT EPS (simplification!)
            historical_pe_series = historical_prices / current_eps
            historical_pe_series = historical_pe_series.dropna()  # Drop NaNs
            data_source = "calculated_fundamental + historical_prices"

            if not historical_pe_series.empty:
                mean_hist_pe = historical_pe_series.mean()
                std_hist_pe = historical_pe_series.std()

                # Check for zero standard deviation BEFORE calculating percentile/z-score
                if std_hist_pe is None or std_hist_pe < 1e-9:
                    logger.warning(f"[{agent_name}] Historical P/E std dev is zero or None for {symbol}. Cannot calculate percentile/z-score.")
                    percentile_rank = None # Ensure these are None
                    z_score = None
                    data_source += " (historical std dev zero)" # Add note to data source
                else:
                    # Calculate percentile rank of current P/E relative to history
                    try:
                        # Use scipy if available for potentially more accurate percentileofscore
                        from scipy import stats

                        percentile_rank = stats.percentileofscore(
                            historical_pe_series, current_pe, kind="rank"
                        )
                    except ImportError:
                        # Fallback numpy/pandas calculation (less precise for ties)
                        percentile_rank = (historical_pe_series < current_pe).mean() * 100

                    # Calculate Z-score (already checked std_hist_pe > 1e-9)
                    z_score = (current_pe - mean_hist_pe) / std_hist_pe
            else:
                logger.warning(
                    f"[{agent_name}] Historical P/E series empty after calculation for {symbol}"
                )
                data_source = "calculated_fundamental (historical calc failed)"
        # This else corresponds to the check after conversion attempt
        elif historical_prices is not None: # It exists but is empty
             logger.warning(f"[{agent_name}] Historical price series is empty for {symbol}")
             data_source = "calculated_fundamental (empty historical data)"
        else: # Conversion failed or original was None
            logger.warning(
                f"[{agent_name}] Invalid or missing historical price series format for {symbol}"
            )
            data_source = "calculated_fundamental (invalid/missing historical data)"

    # Determine Verdict based on Percentile Rank
    # This logic remains largely the same, but now percentile_rank will be None if std dev was zero
    if percentile_rank is None:
        verdict = "NO_HISTORICAL_CONTEXT"
        confidence = 0.3  # Low confidence as only current PE is known
    elif percentile_rank <= pe_settings.PERCENTILE_UNDERVALUED:
        verdict = "UNDERVALUED_REL_HIST"
        # Dynamic confidence: Higher confidence the lower the percentile (closer to 0)
        confidence = 0.6 + 0.3 * (
            1 - (percentile_rank / pe_settings.PERCENTILE_UNDERVALUED)
        )
    elif percentile_rank >= pe_settings.PERCENTILE_OVERVALUED:
        verdict = "OVERVALUED_REL_HIST"
        # Dynamic confidence: Higher confidence the higher the percentile (closer to 100)
        confidence = 0.6 + 0.3 * (
            (percentile_rank - pe_settings.PERCENTILE_OVERVALUED)
            / (100 - pe_settings.PERCENTILE_OVERVALUED)
        )
    else:
        verdict = "FAIRLY_VALUED_REL_HIST"
        confidence = 0.5  # Neutral confidence

    # Ensure confidence is within [0, 1] bounds
    confidence = max(0.0, min(1.0, confidence))

    # Prepare details dictionary
    details = {
        "current_pe_ratio": float(round(current_pe, 2)) if current_pe is not None else None,
        "current_eps": float(round(current_eps, 2)) if current_eps is not None else None,
        "current_price": float(round(current_price, 2)) if current_price is not None else None,
        "historical_mean_pe": (
            float(round(mean_hist_pe, 2)) if mean_hist_pe is not None else None
        ),
        "historical_std_dev_pe": (
            float(round(std_hist_pe, 2)) if std_hist_pe is not None else None
        ),
        "percentile_rank": (
            float(round(percentile_rank, 1)) if percentile_rank is not None else None
        ),
        "z_score": float(round(z_score, 2)) if z_score is not None else None,
        "data_source": data_source,
        "config_used": {
            "historical_years": int(pe_settings.HISTORICAL_YEARS),
            "percentile_undervalued": float(pe_settings.PERCENTILE_UNDERVALUED),
            "percentile_overvalued": float(pe_settings.PERCENTILE_OVERVALUED),
        },
    }

    # Create success result dictionary
    result = {
        "symbol": symbol,
        "verdict": verdict,
        "confidence": float(round(confidence, 4)),
        "value": float(round(current_pe, 2)) if current_pe is not None else None,
        "details": details,
        "agent_name": agent_name,
    }
    return result
