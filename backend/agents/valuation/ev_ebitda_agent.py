import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Assume these data provider functions exist or will be created:
from backend.utils.data_provider import (
    fetch_price_point,
    fetch_latest_ev,
    fetch_latest_ebitda,
    fetch_historical_price_series,
    fetch_historical_ev,
    fetch_historical_ebitda,
)
from loguru import logger
from backend.agents.decorators import standard_agent_execution
from backend.config.settings import get_settings

agent_name = "ev_ebitda_agent"
AGENT_CATEGORY = "valuation"  # Define category for the decorator


@standard_agent_execution(
    agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=3600
)
async def run(symbol: str, agent_outputs: dict = None) -> dict:
    """
    Calculates the Enterprise Value to EBITDA (EV/EBITDA) ratio and assesses valuation relative to historical levels.

    Purpose:
        Determines the current EV/EBITDA ratio and compares it to its historical distribution
        over a configured period (e.g., 5 years). This provides context on whether the current
        valuation is high, low, or fair compared to the company's own past performance.

    Metrics Calculated:
        - Current EV/EBITDA Ratio (Enterprise Value / EBITDA)
        - Historical Mean EV/EBITDA Ratio
        - Historical Standard Deviation of EV/EBITDA Ratio
        - Percentile Rank of Current EV/EBITDA within Historical Distribution
        - Z-Score of Current EV/EBITDA relative to Historical Mean/StdDev

    Logic:
        1. Fetches current EV and EBITDA.
        2. Fetches historical EV and EBITDA series for the configured number of years.
        3. Calculates the current EV/EBITDA ratio. Handles zero or negative EBITDA.
        4. Calculates the historical EV/EBITDA ratio series, aligning EV and EBITDA data and handling periods with non-positive EBITDA.
        5. If historical data is available:
            a. Calculates the mean and standard deviation of the historical EV/EBITDA series.
            b. Calculates the percentile rank of the current ratio within the historical distribution.
            c. Calculates the Z-score of the current ratio.
        6. Determines a verdict based on the percentile rank compared to configured thresholds (PERCENTILE_UNDERVALUED, PERCENTILE_OVERVALUED):
            - If percentile <= PERCENTILE_UNDERVALUED: Verdict is 'UNDERVALUED_REL_HIST'.
            - If percentile >= PERCENTILE_OVERVALUED: Verdict is 'OVERVALUED_REL_HIST'.
            - Otherwise: Verdict is 'FAIRLY_VALUED_REL_HIST'.
            - If historical data is insufficient: Verdict is 'NO_HISTORICAL_CONTEXT'.
            - If current EBITDA <= 0: Verdict is 'NEGATIVE_OR_ZERO'.
        7. Calculates a dynamic confidence score based on the percentile rank relative to the thresholds.
        8. Returns the verdict, confidence, current ratio, and detailed historical metrics.

    Dependencies:
        - Requires data provider functions for current and historical EV and EBITDA.
        - Optionally uses `scipy.stats` for percentile calculation if available, otherwise uses pandas.

    Configuration Used (from settings.py -> AgentSettings -> EvEbitdaAgentSettings):
        - `HISTORICAL_YEARS`: Number of years of historical data to fetch.
        - `PERCENTILE_UNDERVALUED`: Percentile threshold below which the ratio is considered undervalued relative to history.
        - `PERCENTILE_OVERVALUED`: Percentile threshold above which the ratio is considered overvalued relative to history.

    Return Structure:
        A dictionary containing:
        - symbol (str): The stock symbol.
        - verdict (str): 'UNDERVALUED_REL_HIST', 'FAIRLY_VALUED_REL_HIST', 'OVERVALUED_REL_HIST', 'NEGATIVE_OR_ZERO', 'NO_HISTORICAL_CONTEXT', 'NO_DATA'.
        - confidence (float): Dynamic score based on percentile rank (0.0 to 1.0).
        - value (float | None): The current EV/EBITDA ratio, or None if not calculable.
        - details (dict): Contains current EV/EBITDA, historical stats (mean, std dev, percentile, z-score), data source info, and configuration used.
        - agent_name (str): The name of this agent.
        - error (str | None): Error message if an issue occurred (handled by decorator).
    """
    # Fetch settings
    settings = get_settings()
    ev_settings = settings.agent_settings.ev_ebitda

    # Fetch current EV, EBITDA, and historical data concurrently
    # NOTE: Assumes fetch_historical_ev/ebitda return Series aligned with price dates
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=ev_settings.HISTORICAL_YEARS * 365.25) # Approximate years

        ev_task = fetch_latest_ev(symbol)
        ebitda_task = fetch_latest_ebitda(symbol)
        hist_ev_task = fetch_historical_ev(symbol, start_date=start_date.strftime('%Y-%m-%d'), end_date=end_date.strftime('%Y-%m-%d'))
        hist_ebitda_task = fetch_historical_ebitda(
            symbol, start_date=start_date.strftime('%Y-%m-%d'), end_date=end_date.strftime('%Y-%m-%d')
        )

        current_ev, current_ebitda, historical_ev, historical_ebitda = (
            await asyncio.gather(ev_task, ebitda_task, hist_ev_task, hist_ebitda_task)
        )
    except Exception as fetch_err:
        logger.error(f"[{agent_name}] Error fetching data for {symbol}: {fetch_err}")
        return {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {
                "reason": f"Failed to fetch required EV/EBITDA data: {fetch_err}"
            },
            "agent_name": agent_name,
        }

    # Validate fetched data
    if current_ev is None or current_ebitda is None:
        return {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {
                "reason": f"Missing current EV ({current_ev}) or EBITDA ({current_ebitda})"
            },
            "agent_name": agent_name,
        }
    if current_ebitda <= 0:
        return {
            "symbol": symbol,
            "verdict": "NEGATIVE_OR_ZERO",
            "confidence": 0.7,
            "value": None,
            "details": {
                "current_ebitda": current_ebitda,
                "reason": "EBITDA is zero or negative",
            },
            "agent_name": agent_name,
        }

    # Calculate Current EV/EBITDA Ratio
    current_ev_ebitda = current_ev / current_ebitda

    # Calculate Historical EV/EBITDA Analysis
    historical_ev_ebitda_series = None
    mean_hist_ev_ebitda = None
    std_hist_ev_ebitda = None
    percentile_rank = None
    z_score = None
    data_source = "calculated_fundamental"

    # Check if BOTH historical series are valid pandas Series
    valid_hist_ev = isinstance(historical_ev, pd.Series) and not historical_ev.empty
    valid_hist_ebitda = (
        isinstance(historical_ebitda, pd.Series) and not historical_ebitda.empty
    )

    if valid_hist_ev and valid_hist_ebitda:
        # Align historical data on common index
        common_index = historical_ev.index.intersection(historical_ebitda.index)
        if not common_index.empty:
            aligned_ev = historical_ev.loc[common_index]
            aligned_ebitda = historical_ebitda.loc[common_index]

            # Filter out periods where EBITDA is zero or negative to avoid division errors/meaningless ratios
            valid_ebitda_mask = aligned_ebitda > 0
            if valid_ebitda_mask.any():
                historical_ev_ebitda_series = (
                    aligned_ev[valid_ebitda_mask] / aligned_ebitda[valid_ebitda_mask]
                ).dropna()
                data_source = "calculated_fundamental + historical_ev_ebitda"

                if not historical_ev_ebitda_series.empty:
                    mean_hist_ev_ebitda = historical_ev_ebitda_series.mean()
                    std_hist_ev_ebitda = historical_ev_ebitda_series.std()

                    # Calculate percentile rank
                    try:
                        from scipy import stats

                        percentile_rank = stats.percentileofscore(
                            historical_ev_ebitda_series, current_ev_ebitda, kind="rank"
                        )
                    except ImportError:
                        percentile_rank = (
                            historical_ev_ebitda_series < current_ev_ebitda
                        ).mean() * 100

                    # Calculate Z-score
                    if std_hist_ev_ebitda and std_hist_ev_ebitda > 1e-9:
                        z_score = (
                            current_ev_ebitda - mean_hist_ev_ebitda
                        ) / std_hist_ev_ebitda
                else:
                    logger.warning(
                        f"[{agent_name}] Historical EV/EBITDA series empty after calculation for {symbol}"
                    )
                    data_source = "calculated_fundamental (historical calc failed)"
            else:
                logger.warning(
                    f"[{agent_name}] No valid historical EBITDA (>0) found for {symbol}"
                )
                data_source = "calculated_fundamental (no positive historical EBITDA)"
        else:
            logger.warning(
                f"[{agent_name}] No common index for historical EV and EBITDA for {symbol}"
            )
            data_source = "calculated_fundamental (historical alignment failed)"
    else:
        logger.warning(
            f"[{agent_name}] Missing or invalid historical EV/EBITDA data for {symbol}"
        )
        data_source = "calculated_fundamental (missing historical data)"

    # Determine Verdict based on Percentile Rank
    if percentile_rank is None:
        verdict = "NO_HISTORICAL_CONTEXT"
        confidence = 0.3
    elif percentile_rank <= ev_settings.PERCENTILE_UNDERVALUED:
        verdict = "UNDERVALUED_REL_HIST"
        confidence = 0.6 + 0.3 * (
            1 - (percentile_rank / ev_settings.PERCENTILE_UNDERVALUED)
        )
    elif percentile_rank >= ev_settings.PERCENTILE_OVERVALUED:
        verdict = "OVERVALUED_REL_HIST"
        confidence = 0.6 + 0.3 * (
            (percentile_rank - ev_settings.PERCENTILE_OVERVALUED)
            / (100 - ev_settings.PERCENTILE_OVERVALUED)
        )
    else:
        verdict = "FAIRLY_VALUED_REL_HIST"
        confidence = 0.5

    # Ensure confidence is within [0, 1] bounds
    confidence = max(0.0, min(1.0, confidence))

    # Prepare details dictionary
    details = {
        "current_ev_ebitda_ratio": round(current_ev_ebitda, 2),
        "current_ev": current_ev,  # Keep raw values for context
        "current_ebitda": current_ebitda,
        "historical_mean_ev_ebitda": (
            round(mean_hist_ev_ebitda, 2) if mean_hist_ev_ebitda is not None else None
        ),
        "historical_std_dev_ev_ebitda": (
            round(std_hist_ev_ebitda, 2) if std_hist_ev_ebitda is not None else None
        ),
        "percentile_rank": (
            round(percentile_rank, 1) if percentile_rank is not None else None
        ),
        "z_score": round(z_score, 2) if z_score is not None else None,
        "data_source": data_source,
        "config_used": {
            "historical_years": ev_settings.HISTORICAL_YEARS,
            "percentile_undervalued": ev_settings.PERCENTILE_UNDERVALUED,
            "percentile_overvalued": ev_settings.PERCENTILE_OVERVALUED,
        },
    }

    # Create success result dictionary
    result = {
        "symbol": symbol,
        "verdict": verdict,
        "confidence": round(confidence, 4),
        "value": round(current_ev_ebitda, 2),
        "details": details,
        "agent_name": agent_name,
    }
    return result
