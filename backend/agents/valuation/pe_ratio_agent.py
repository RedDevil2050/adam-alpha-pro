import asyncio
import pandas as pd
import numpy as np
from backend.utils.data_provider import fetch_price_point, fetch_latest_eps, fetch_historical_price_series # Updated imports
from loguru import logger
from backend.agents.decorators import standard_agent_execution
from backend.config.settings import get_settings

agent_name = "pe_ratio_agent"
AGENT_CATEGORY = "valuation" # Define category for the decorator

@standard_agent_execution(agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=3600)
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
        eps_task = fetch_latest_eps(symbol)
        hist_price_task = fetch_historical_price_series(symbol, years=pe_settings.HISTORICAL_YEARS)
        price_data, current_eps, historical_prices = await asyncio.gather(price_task, eps_task, hist_price_task)
    except Exception as fetch_err:
        logger.error(f"[{agent_name}] Error fetching data for {symbol}: {fetch_err}")
        return {
            "symbol": symbol, "verdict": "NO_DATA", "confidence": 0.0, "value": None,
            "details": {"reason": f"Failed to fetch required data: {fetch_err}"},
            "agent_name": agent_name
        }

    current_price = price_data.get("latestPrice") if price_data else None

    # Validate fetched data
    if current_price is None or current_price <= 0:
        return {
            "symbol": symbol, "verdict": "NO_DATA", "confidence": 0.0, "value": None,
            "details": {"reason": f"Missing or invalid current price: {current_price}"},
            "agent_name": agent_name
        }
    if current_eps is None:
        return {
            "symbol": symbol, "verdict": "NO_DATA", "confidence": 0.0, "value": None,
            "details": {"reason": "Missing EPS data"},
            "agent_name": agent_name
        }
    if current_eps <= 0:
        return {
            "symbol": symbol, "verdict": "NEGATIVE_EARNINGS", "confidence": 0.7, "value": None,
            "details": {"current_eps": current_eps, "reason": "EPS is zero or negative"},
            "agent_name": agent_name
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

    if historical_prices is not None and not historical_prices.empty:
        # Ensure historical_prices is a pandas Series
        if not isinstance(historical_prices, pd.Series):
             try:
                 # Attempt conversion assuming dict {date: price} or similar
                 historical_prices = pd.Series(historical_prices)
                 historical_prices.index = pd.to_datetime(historical_prices.index)
             except Exception as conversion_err:
                 logger.warning(f"[{agent_name}] Could not convert historical_prices to Series for {symbol}: {conversion_err}")
                 historical_prices = None # Invalidate if conversion fails

        if historical_prices is not None and not historical_prices.empty:
            # Calculate historical P/E using historical prices and CURRENT EPS (simplification!)
            historical_pe_series = historical_prices / current_eps
            historical_pe_series = historical_pe_series.dropna() # Drop NaNs
            data_source = "calculated_fundamental + historical_prices"

            if not historical_pe_series.empty:
                mean_hist_pe = historical_pe_series.mean()
                std_hist_pe = historical_pe_series.std()

                # Calculate percentile rank of current P/E relative to history
                try:
                    # Use scipy if available for potentially more accurate percentileofscore
                    from scipy import stats
                    percentile_rank = stats.percentileofscore(historical_pe_series, current_pe, kind='rank')
                except ImportError:
                    # Fallback numpy/pandas calculation (less precise for ties)
                    percentile_rank = (historical_pe_series < current_pe).mean() * 100

                # Calculate Z-score
                if std_hist_pe and std_hist_pe > 1e-9: # Avoid division by near-zero
                     z_score = (current_pe - mean_hist_pe) / std_hist_pe
            else:
                 logger.warning(f"[{agent_name}] Historical P/E series empty after calculation for {symbol}")
                 data_source = "calculated_fundamental (historical calc failed)"
        else:
             logger.warning(f"[{agent_name}] Invalid historical price series format for {symbol}")
             data_source = "calculated_fundamental (invalid historical data)"

    # Determine Verdict based on Percentile Rank
    if percentile_rank is None:
        verdict = "NO_HISTORICAL_CONTEXT"
        confidence = 0.3 # Low confidence as only current PE is known
    elif percentile_rank <= pe_settings.PERCENTILE_UNDERVALUED:
        verdict = "UNDERVALUED_REL_HIST"
        # Dynamic confidence: Higher confidence the lower the percentile (closer to 0)
        confidence = 0.6 + 0.3 * (1 - (percentile_rank / pe_settings.PERCENTILE_UNDERVALUED))
    elif percentile_rank >= pe_settings.PERCENTILE_OVERVALUED:
        verdict = "OVERVALUED_REL_HIST"
        # Dynamic confidence: Higher confidence the higher the percentile (closer to 100)
        confidence = 0.6 + 0.3 * ((percentile_rank - pe_settings.PERCENTILE_OVERVALUED) / (100 - pe_settings.PERCENTILE_OVERVALUED))
    else:
        verdict = "FAIRLY_VALUED_REL_HIST"
        confidence = 0.5 # Neutral confidence

    # Ensure confidence is within [0, 1] bounds
    confidence = max(0.0, min(1.0, confidence))

    # Prepare details dictionary
    details = {
        "current_pe_ratio": round(current_pe, 2),
        "current_eps": round(current_eps, 2),
        "current_price": round(current_price, 2),
        "historical_mean_pe": round(mean_hist_pe, 2) if mean_hist_pe is not None else None,
        "historical_std_dev_pe": round(std_hist_pe, 2) if std_hist_pe is not None else None,
        "percentile_rank": round(percentile_rank, 1) if percentile_rank is not None else None,
        "z_score": round(z_score, 2) if z_score is not None else None,
        "data_source": data_source,
        "config_used": {
            "historical_years": pe_settings.HISTORICAL_YEARS,
            "percentile_undervalued": pe_settings.PERCENTILE_UNDERVALUED,
            "percentile_overvalued": pe_settings.PERCENTILE_OVERVALUED
        }
    }

    # Create success result dictionary
    result = {
        "symbol": symbol,
        "verdict": verdict,
        "confidence": round(confidence, 4),
        "value": round(current_pe, 2),
        "details": details,
        "agent_name": agent_name
    }
    return result
