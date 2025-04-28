import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

import asyncio
import pandas as pd
import numpy as np
from backend.utils.data_provider import fetch_price_point, fetch_book_value, fetch_historical_price_series
from loguru import logger
from backend.agents.decorators import standard_agent_execution
from backend.config.settings import get_settings

agent_name = "book_to_market_agent"
AGENT_CATEGORY = "valuation"

@standard_agent_execution(agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=3600)
async def run(symbol: str, agent_outputs: dict = None) -> dict:
    """
    Calculates the Book-to-Market (B/M) ratio for a given stock symbol and assesses its valuation
    relative to its own historical values.

    Purpose:
        Determines the B/M ratio, which compares a company's book value (accounting value) to its market value.
        It then compares the current ratio to the stock's own historical distribution to determine
        if the stock is currently undervalued or overvalued relative to its historical context.

    Metrics Calculated:
        - Book-to-Market Ratio (Book Value per Share / Market Price per Share)
        - Historical Mean B/M Ratio
        - Historical Standard Deviation of B/M Ratio
        - Percentile Rank of Current B/M within Historical Distribution
        - Z-Score of Current B/M relative to Historical Mean/StdDev

    Logic:
        1. Fetches the latest stock price and book value per share.
        2. Validates that both price and book value are available and positive.
        3. Calculates the current B/M ratio.
        4. Fetches historical price data and calculates historical B/M ratios (using current book value).
        5. Calculates statistical measures of the B/M ratio's historical distribution.
        6. Determines a verdict based on the percentile rank compared to configured thresholds:
           - High B/M (>75th percentile) is considered 'UNDERVALUED_REL_HIST'
           - Low B/M (<25th percentile) is considered 'OVERVALUED_REL_HIST'
           - B/M in between is considered 'FAIRLY_VALUED_REL_HIST'
        7. Sets a dynamic confidence score based on the percentile rank's distance from thresholds.

    Dependencies:
        - Requires latest stock price (`fetch_price_point`).
        - Requires book value per share (`fetch_book_value`).
        - Requires historical price data (`fetch_historical_price_series`).

    Configuration Used:
        - `settings.agent_settings.book_to_market.HISTORICAL_YEARS`: Years of historical data to use.
        - `settings.agent_settings.book_to_market.PERCENTILE_UNDERVALUED`: Percentile threshold for undervaluation.
        - `settings.agent_settings.book_to_market.PERCENTILE_OVERVALUED`: Percentile threshold for overvaluation.

    Return Structure:
        A dictionary containing:
        - symbol (str): The stock symbol.
        - verdict (str): 'UNDERVALUED_REL_HIST', 'FAIRLY_VALUED_REL_HIST', 'OVERVALUED_REL_HIST', 
                         'NEGATIVE_OR_ZERO_BV', 'NO_HISTORICAL_CONTEXT', or 'NO_DATA'.
        - confidence (float): A dynamic score based on the percentile rank (0.0 to 1.0).
        - value (float | None): The calculated B/M ratio, or None if not available/applicable.
        - details (dict): Contains book value, price, B/M ratio, historical stats, data source, and configuration used.
        - agent_name (str): The name of this agent.
        - error (str | None): Error message if an issue occurred (handled by decorator).
    """
    # Fetch settings
    settings = get_settings()
    btm_settings = settings.agent_settings.book_to_market

    # Fetch data concurrently
    price_task = fetch_price_point(symbol)
    book_value_task = fetch_book_value(symbol)
    
    price, book_value = await asyncio.gather(price_task, book_value_task)

    # Validate data
    if price is None or book_value is None or price <= 0:
        # Return NO_DATA format
        details = {
            "book_value_per_share": book_value,
            "latest_price": price,
            "reason": f"Missing or invalid data (Price: {price}, Book Value: {book_value})"
        }
        return {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": details,
            "agent_name": agent_name
        }

    # Calculate Current B/M Ratio
    btm_ratio = book_value / price

    # Calculate Historical B/M Analysis
    historical_btm_series = None
    mean_hist_btm = None
    std_hist_btm = None
    percentile_rank = None
    z_score = None
    data_source = "calculated_fundamental"

    # Fetch historical prices
    try:
        historical_prices = await fetch_historical_price_series(symbol, years=btm_settings.HISTORICAL_YEARS)
    except Exception as fetch_err:
        logger.warning(f"[{agent_name}] Failed to fetch historical prices for {symbol}: {fetch_err}. Proceeding without historical context.")
        historical_prices = None

    if historical_prices is not None and not historical_prices.empty:
        # Ensure historical_prices is a pandas Series
        if not isinstance(historical_prices, pd.Series):
             try:
                 historical_prices = pd.Series(historical_prices)
                 historical_prices.index = pd.to_datetime(historical_prices.index)
             except Exception as conversion_err:
                 logger.warning(f"[{agent_name}] Could not convert historical_prices to Series for {symbol}: {conversion_err}")
                 historical_prices = None

        if historical_prices is not None and not historical_prices.empty:
            # Calculate historical B/M using CURRENT book_value and historical prices (simplification!)
            # Filter out non-positive prices before division
            positive_prices = historical_prices[historical_prices > 0]
            if not positive_prices.empty:
                historical_btm_series = book_value / positive_prices
                historical_btm_series = historical_btm_series.dropna()
                data_source = "calculated_fundamental + historical_prices"

                if not historical_btm_series.empty:
                    mean_hist_btm = historical_btm_series.mean()
                    std_hist_btm = historical_btm_series.std()

                    # Calculate percentile rank of current B/M relative to history
                    try:
                        from scipy import stats
                        percentile_rank = stats.percentileofscore(historical_btm_series, btm_ratio, kind='rank')
                    except ImportError:
                        percentile_rank = (historical_btm_series < btm_ratio).mean() * 100

                    # Calculate Z-score
                    if std_hist_btm and std_hist_btm > 1e-9:
                         z_score = (btm_ratio - mean_hist_btm) / std_hist_btm
                else:
                    logger.warning(f"[{agent_name}] Historical B/M series empty after calculation for {symbol}")
                    data_source = "calculated_fundamental (historical calc failed)"
            else:
                logger.warning(f"[{agent_name}] No positive historical prices found for B/M calculation for {symbol}")
                data_source = "calculated_fundamental (no positive historical prices)"
        else:
             logger.warning(f"[{agent_name}] Invalid historical price series format for {symbol}")
             data_source = "calculated_fundamental (invalid historical data)"

    # Determine Verdict based on Percentile Rank (Note: High B/M is Undervalued)
    if book_value <= 0: # Check book value itself first
        verdict = "NEGATIVE_OR_ZERO_BV"
        confidence = 0.7
    elif percentile_rank is None:
        verdict = "NO_HISTORICAL_CONTEXT"
        confidence = 0.3
    elif percentile_rank >= btm_settings.PERCENTILE_UNDERVALUED: # High percentile means high B/M -> Undervalued
        verdict = "UNDERVALUED_REL_HIST"
        confidence = 0.6 + 0.3 * ((percentile_rank - btm_settings.PERCENTILE_UNDERVALUED) / (100 - btm_settings.PERCENTILE_UNDERVALUED))
    elif percentile_rank <= btm_settings.PERCENTILE_OVERVALUED: # Low percentile means low B/M -> Overvalued
        verdict = "OVERVALUED_REL_HIST"
        confidence = 0.6 + 0.3 * (1 - (percentile_rank / btm_settings.PERCENTILE_OVERVALUED))
    else:
        verdict = "FAIRLY_VALUED_REL_HIST"
        confidence = 0.5

    # Ensure confidence is within [0, 1] bounds
    confidence = max(0.0, min(1.0, confidence))

    # Prepare details dictionary
    details = {
        "btm_ratio": round(btm_ratio, 4),
        "book_value_per_share": round(book_value, 4),
        "latest_price": round(price, 4),
        "historical_mean_btm": round(mean_hist_btm, 4) if mean_hist_btm is not None else None,
        "historical_std_dev_btm": round(std_hist_btm, 4) if std_hist_btm is not None else None,
        "percentile_rank": round(percentile_rank, 1) if percentile_rank is not None else None,
        "z_score": round(z_score, 2) if z_score is not None else None,
        "data_source": data_source,
        "config_used": {
            "historical_years": btm_settings.HISTORICAL_YEARS,
            "percentile_undervalued": btm_settings.PERCENTILE_UNDERVALUED,
            "percentile_overvalued": btm_settings.PERCENTILE_OVERVALUED
        }
    }

    # Create success result dictionary
    result = {
        "symbol": symbol,
        "verdict": verdict,
        "confidence": round(confidence, 4),
        "value": round(btm_ratio, 4),
        "details": details,
        "agent_name": agent_name
    }
    return result
