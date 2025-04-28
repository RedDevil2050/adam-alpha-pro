from backend.utils.data_provider import fetch_price_series
from backend.config.settings import get_settings
import numpy as np
import pandas as pd
from loguru import logger
from backend.agents.decorators import standard_agent_execution

agent_name = "correlation_agent"
AGENT_CATEGORY = "market"

@standard_agent_execution(agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=3600)
async def run(symbol: str, agent_outputs: dict = None) -> dict:
    """
    Calculates the correlation between a stock symbol and the market index over different time periods.

    Purpose:
        Measures the linear relationship (correlation) between a stock's returns and the market's returns,
        which helps assess how much the stock's price movements are related to overall market movements.
        High correlation suggests the stock tends to move with the market, while low correlation suggests
        more independent price action.

    Metrics Calculated:
        - 30-day correlation between stock and market returns
        - 60-day correlation between stock and market returns (if sufficient data)

    Logic:
        1. Fetches price series for both the stock symbol and the configured market index.
        2. Calculates daily percentage returns for both series.
        3. Aligns the return series by date to ensure matching periods.
        4. Calculates the correlation coefficient over 30-day and 60-day windows.
        5. Determines a verdict based on the 30-day correlation level compared to configured thresholds:
           - HIGH_CORRELATION if correlation > settings.THRESHOLD_HIGH_CORRELATION
           - LOW_CORRELATION if correlation < settings.THRESHOLD_LOW_CORRELATION
           - NORMAL_CORRELATION otherwise
        6. Sets a confidence score based on the strength/clarity of the correlation pattern.

    Dependencies:
        - Requires price series data for both the stock and market index.
        - Uses the market index symbol defined in settings.data_provider.MARKET_INDEX_SYMBOL.

    Configuration Used:
        - `settings.correlation.MIN_REQUIRED_DAYS`: Minimum days of data required for correlation calculation.
        - `settings.correlation.MIN_DAYS_FOR_30D_CORR`: Minimum days needed for 30-day correlation.
        - `settings.correlation.THRESHOLD_HIGH_CORRELATION`: Threshold above which correlation is considered high.
        - `settings.correlation.THRESHOLD_LOW_CORRELATION`: Threshold below which correlation is considered low.
        - `settings.data_provider.MARKET_INDEX_SYMBOL`: The market index symbol to use for correlation.

    Return Structure:
        A dictionary containing:
        - symbol (str): The input stock symbol.
        - verdict (str): 'HIGH_CORRELATION', 'NORMAL_CORRELATION', 'LOW_CORRELATION', or 'NO_DATA'.
        - confidence (float): A fixed confidence value based on the verdict (0.0 to 1.0).
        - value (float | None): The calculated 30-day correlation coefficient, or None if unavailable.
        - details (dict): Contains 30-day and 60-day correlations, and the market index used.
        - agent_name (str): The name of this agent.
        - error (str | None): Error message if an issue occurred (handled by decorator).
    """
    # Get settings
    settings = get_settings()
    corr_settings = settings.agent_settings.correlation

    # Get price data for symbol and market index
    symbol_prices = await fetch_price_series(symbol)
    # Use market index from config
    market_symbol = settings.data_provider.MARKET_INDEX_SYMBOL
    market_prices = await fetch_price_series(market_symbol)

    # Use settings for minimum days required
    min_days = corr_settings.MIN_REQUIRED_DAYS
    if not symbol_prices or not market_prices or len(symbol_prices) < min_days or len(market_prices) < min_days:
        # Return NO_DATA format
        return {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {"reason": f"Insufficient price history for {symbol} or market index {market_symbol} (need {min_days} days)"},
            "agent_name": agent_name
        }

    # Calculate returns
    sym_series = pd.Series(symbol_prices)
    mkt_series = pd.Series(market_prices)
    sym_ret = sym_series.pct_change().dropna()
    mkt_ret = mkt_series.pct_change().dropna()

    # Align returns (simple intersection)
    common_index = sym_ret.index.intersection(mkt_ret.index)
    if len(common_index) < min_days:
        return {
            "symbol": symbol, "verdict": "NO_DATA", "confidence": 0.0, "value": None,
            "details": {"reason": f"Insufficient overlapping data points ({len(common_index)} < {min_days}) between {symbol} and {market_symbol}"},
            "agent_name": agent_name
        }
    sym_ret = sym_ret.loc[common_index]
    mkt_ret = mkt_ret.loc[common_index]

    # Use settings for minimum days for 30-day correlation
    min_days_30d = corr_settings.MIN_DAYS_FOR_30D_CORR
    if len(sym_ret) < min_days_30d or len(mkt_ret) < min_days_30d:
        return {
            "symbol": symbol, "verdict": "NO_DATA", "confidence": 0.0, "value": None,
            "details": {"reason": f"Insufficient aligned data points for 30d correlation ({len(sym_ret)} points)"},
            "agent_name": agent_name
        }

    # Calculate rolling correlations
    # Use tail for recent data
    correlation_30d = sym_ret.tail(30).corr(mkt_ret.tail(30))
    correlation_60d = sym_ret.tail(60).corr(mkt_ret.tail(60)) if len(sym_ret) >= 60 else np.nan

    # Handle potential NaN correlations
    if np.isnan(correlation_30d):
        return {
            "symbol": symbol, "verdict": "NO_DATA", "confidence": 0.0, "value": None,
            "details": {"reason": "Could not calculate 30d correlation (NaN result)", "market_index": market_symbol},
            "agent_name": agent_name
        }

    # Use settings for correlation thresholds
    high_corr_threshold = corr_settings.THRESHOLD_HIGH_CORRELATION
    low_corr_threshold = corr_settings.THRESHOLD_LOW_CORRELATION

    # Simplified Verdict Logic based on 30d correlation and settings thresholds
    if correlation_30d > high_corr_threshold:
        verdict = "HIGH_CORRELATION"
        confidence = 0.8 # Adjusted confidence
    elif correlation_30d < low_corr_threshold:
        verdict = "LOW_CORRELATION"
        confidence = 0.7 # Adjusted confidence
    else:
        verdict = "NORMAL_CORRELATION"
        confidence = 0.6

    # Create success result dictionary
    result = {
        "symbol": symbol,
        "verdict": verdict,
        "confidence": round(confidence, 4),
        "value": round(correlation_30d, 4), # 30d correlation as primary value
        "details": {
            "correlation_30d": round(correlation_30d, 4),
            "correlation_60d": round(correlation_60d, 4) if not np.isnan(correlation_60d) else None,
            "market_index_used": market_symbol,
            "config_used": {
                "high_correlation_threshold": high_corr_threshold,
                "low_correlation_threshold": low_corr_threshold,
                "min_required_days": min_days
            }
        },
        "agent_name": agent_name
    }

    return result
