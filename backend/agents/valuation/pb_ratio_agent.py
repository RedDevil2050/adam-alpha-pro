import asyncio
import pandas as pd
import numpy as np
from backend.utils.data_provider import (
    fetch_price_point,
    fetch_latest_bvps,  # Corrected import
    fetch_historical_price_series,
)  # Updated imports
from loguru import logger
from backend.agents.decorators import standard_agent_execution
from backend.config.settings import get_settings
from datetime import datetime, timedelta

agent_name = "pb_ratio_agent"
AGENT_CATEGORY = "valuation"  # Define category for the decorator


@standard_agent_execution(
    agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=3600
)
async def run(symbol: str, agent_outputs: dict = None) -> dict:
    """
    Calculates the Price-to-Book (P/B) ratio for a given stock symbol and assesses its valuation
    relative to its historical P/B range.

    Purpose:
        Determines the current P/B ratio and compares it to the stock's historical P/B distribution
        to assess if it's currently undervalued, fairly valued, or overvalued relative to its own past.

    Metrics Calculated:
        - Current P/B Ratio (Current Price / Latest Book Value Per Share (BVPS))
        - Historical Mean P/B Ratio (over a configured period)
        - Historical Standard Deviation of P/B Ratio
        - Percentile Rank of Current P/B within its historical distribution
        - Z-Score of Current P/B relative to its historical mean and standard deviation

    Logic:
        1. Fetches current price, latest BVPS, and historical price series concurrently.
        2. Validates fetched data (price > 0, BVPS available and > 0). Returns 'NO_DATA' or 'NEGATIVE_OR_ZERO_BV' if validation fails.
        3. Calculates the current P/B ratio.
        4. If historical price data is available:
           a. Calculates a historical P/B series using historical prices and the *current* BVPS (simplification).
           b. Calculates the mean and standard deviation of the historical P/B series.
           c. Calculates the percentile rank of the current P/B within the historical distribution.
           d. Calculates the Z-score of the current P/B.
        5. Determines a verdict based on the percentile rank compared to configured thresholds:
           - 'UNDERVALUED_REL_HIST' if percentile <= lower threshold.
           - 'OVERVALUED_REL_HIST' if percentile >= upper threshold.
           - 'FAIRLY_VALUED_REL_HIST' otherwise.
           - 'NO_HISTORICAL_CONTEXT' if historical analysis could not be performed.
        6. Calculates a dynamic confidence score based on the percentile rank (higher confidence for extreme percentiles).
        7. Returns the results including the current P/B, verdict, confidence, and detailed historical metrics.

    Dependencies:
        - Requires current stock price (`fetch_price_point`).
        - Requires latest Book Value Per Share (BVPS) (`fetch_latest_bvps`).
        - Requires historical price series (`fetch_historical_price_series`).

    Configuration Used (from settings.py):
        - `agent_settings.pb_ratio.HISTORICAL_YEARS`: Number of years for historical price data.
        - `agent_settings.pb_ratio.PERCENTILE_UNDERVALUED`: Percentile threshold below which P/B is considered undervalued relative to history.
        - `agent_settings.pb_ratio.PERCENTILE_OVERVALUED`: Percentile threshold above which P/B is considered overvalued relative to history.

    Return Structure:
        A dictionary containing:
        - symbol (str): The stock symbol.
        - verdict (str): Valuation verdict relative to history.
        - confidence (float): Dynamic confidence score (0.0 to 1.0).
        - value (float | None): The current P/B ratio.
        - details (dict): Contains current P/B, BVPS, price, historical stats (mean, std dev, percentile, z-score), data source, and config used.
        - agent_name (str): The name of this agent.
        - error (str | None): Error message if an issue occurred (handled by decorator).
    """
    # Fetch settings
    settings = get_settings()
    pb_settings = settings.agent_settings.pb_ratio

    # Fetch current price, latest BVPS, and historical prices concurrently
    try:
        price_task = fetch_price_point(symbol)
        bvps_task = fetch_latest_bvps(symbol)  # Corrected call
        
        # Convert years to start_date and end_date
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=pb_settings.HISTORICAL_YEARS * 365)).strftime("%Y-%m-%d")
        
        hist_price_task = fetch_historical_price_series(
            symbol, start_date=start_date, end_date=end_date
        )
        price_data, current_bvps_data, historical_prices = await asyncio.gather(  # Renamed variable
            price_task, bvps_task, hist_price_task
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
        }

    current_price = price_data.get("latestPrice") if price_data else None
    # Extract BVPS value from the fetched data
    current_bvps = current_bvps_data.get("bookValuePerShare") if current_bvps_data else None

    # --- Start: Added Type Check/Conversion --- 
    # Ensure historical_prices is a pandas Series before further checks
    if historical_prices is not None and not isinstance(historical_prices, pd.Series):
        try:
            logger.debug(f"[{agent_name}] Attempting conversion of historical_prices for {symbol}")
            # Try converting dictionary values if it's a dict, else assume list/iterable
            if isinstance(historical_prices, dict):
                historical_prices = pd.Series(historical_prices)
            else:
                 # Attempt conversion, assuming index might be date-like if possible
                 temp_series = pd.Series(historical_prices)
                 try:
                     temp_series.index = pd.to_datetime(temp_series.index)
                 except (TypeError, ValueError):
                     logger.warning(f"[{agent_name}] Could not convert index to datetime for {symbol}, using default index.")
                 historical_prices = temp_series

            # Check if conversion resulted in an empty series
            if historical_prices.empty:
                 logger.warning(f"[{agent_name}] Historical prices became empty after conversion for {symbol}")
                 historical_prices = None # Treat as no data if empty after conversion

        except Exception as conversion_err:
            logger.warning(
                f"[{agent_name}] Could not convert historical_prices to Series for {symbol}: {conversion_err}"
            )
            historical_prices = None # Treat as no data if conversion fails
    # --- End: Added Type Check/Conversion ---

    # Validate fetched data
    if current_price is None or current_price <= 0:
        return {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {"reason": f"Missing or invalid current price: {current_price}"},
            "agent_name": agent_name,
        }
    if current_bvps is None:
        return {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {"reason": "Missing Book Value Per Share (BVPS) data"},
            "agent_name": agent_name,
        }
    if current_bvps <= 0:
        return {
            "symbol": symbol,
            "verdict": "NEGATIVE_OR_ZERO_BV",
            "confidence": 0.7,
            "value": None,
            "details": {
                "current_bvps": current_bvps,
                "reason": "Book Value Per Share is zero or negative",
            },
            "agent_name": agent_name,
        }

    # Calculate Current P/B Ratio
    current_pb = current_price / current_bvps

    # Calculate Historical P/B Analysis
    historical_pb_series = None
    mean_hist_pb = None
    std_hist_pb = None
    percentile_rank = None
    z_score = None
    data_source = "calculated_fundamental"

    # --- Start: Modified Historical Analysis Block ---
    if historical_prices is not None and not historical_prices.empty: # Check moved earlier is now redundant if conversion handles empty
        # Calculate historical P/B using historical prices and CURRENT BVPS (simplification!)
        historical_pb_series = historical_prices / current_bvps
        historical_pb_series = historical_pb_series.replace([np.inf, -np.inf], np.nan).dropna()
        data_source = "calculated_fundamental + historical_prices"

        if not historical_pb_series.empty:
            mean_hist_pb = historical_pb_series.mean()
            std_hist_pb = historical_pb_series.std()

            # If standard deviation is effectively zero, historical context is not meaningful
            if std_hist_pb is None or std_hist_pb < 1e-9:
                logger.warning(f"[{agent_name}] Historical P/B std dev is zero or None for {symbol}. No context.")
                percentile_rank = None # Force NO_HISTORICAL_CONTEXT verdict
                data_source = "calculated_fundamental (historical std dev zero)"
            else:
                # Calculate percentile rank of current P/B relative to history
                try:
                    from scipy import stats
                    percentile_rank = stats.percentileofscore(
                        historical_pb_series, current_pb, kind="rank"
                    )
                except ImportError:
                    logger.warning("Scipy not installed, using pandas for percentile calculation.")
                    percentile_rank = (historical_pb_series < current_pb).mean() * 100

                # Calculate Z-score (already correctly checks std_hist_pb)
                z_score = (current_pb - mean_hist_pb) / std_hist_pb
        else:
            logger.warning(
                f"[{agent_name}] Historical P/B series empty after calculation/dropna for {symbol}"
            )
            data_source = "calculated_fundamental (historical calc resulted in empty)"
    # --- End: Modified Historical Analysis Block ---

    # Determine Verdict based on Percentile Rank
    if percentile_rank is None:
        verdict = "NO_HISTORICAL_CONTEXT"
        confidence = 0.3
    elif percentile_rank <= pb_settings.PERCENTILE_UNDERVALUED:
        verdict = "UNDERVALUED_REL_HIST"
        confidence = 0.6 + 0.3 * (
            1 - (percentile_rank / pb_settings.PERCENTILE_UNDERVALUED)
        )
    elif percentile_rank >= pb_settings.PERCENTILE_OVERVALUED:
        verdict = "OVERVALUED_REL_HIST"
        confidence = 0.6 + 0.3 * (
            (percentile_rank - pb_settings.PERCENTILE_OVERVALUED)
            / (100 - pb_settings.PERCENTILE_OVERVALUED)
        )
    else:
        verdict = "FAIRLY_VALUED_REL_HIST"
        confidence = 0.5

    # Ensure confidence is within [0, 1] bounds
    confidence = max(0.0, min(1.0, confidence))

    # Prepare details dictionary
    details = {
        "current_pb_ratio": round(current_pb, 2),
        "current_bvps": round(current_bvps, 2),
        "current_price": round(current_price, 2),
        "historical_mean_pb": (
            round(mean_hist_pb, 2) if mean_hist_pb is not None else None
        ),
        "historical_std_dev_pb": (
            round(std_hist_pb, 2) if std_hist_pb is not None else None
        ),
        "percentile_rank": (
            round(percentile_rank, 1) if percentile_rank is not None else None
        ),
        "z_score": round(z_score, 2) if z_score is not None else None,
        "data_source": data_source,
        "config_used": {
            "historical_years": pb_settings.HISTORICAL_YEARS,
            "percentile_undervalued": pb_settings.PERCENTILE_UNDERVALUED,
            "percentile_overvalued": pb_settings.PERCENTILE_OVERVALUED,
        },
    }

    # Create success result dictionary
    result = {
        "symbol": symbol,
        "verdict": verdict,
        "confidence": round(confidence, 4),
        "value": round(current_pb, 2),
        "details": details,
        "agent_name": agent_name,
    }
    return result
