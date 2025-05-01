# filepath: d:\Zion\backend\agents\market\market_regime_agent.py
import pandas as pd
import numpy as np
import logging
from backend.utils.data_provider import fetch_price_series
from backend.config.settings import get_settings
from backend.agents.decorators import standard_agent_execution

logger = logging.getLogger(__name__)
agent_name = "market_regime_agent"
AGENT_CATEGORY = "market"

@standard_agent_execution(
    agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=3600
)
async def run(symbol: str, agent_outputs: dict = None) -> dict:
    """
    Determines the current market regime based on the market index's price action.

    Purpose:
        Provides context about the overall market trend (e.g., Bullish, Bearish, Neutral)
        which can be used by other agents to adjust their signals or confidence.

    Metrics Calculated:
        - Market Regime (e.g., 'BULL', 'BEAR', 'NEUTRAL') based on SMA comparison.

    Logic:
        1. Fetches historical price series for the configured market index.
        2. Validates the fetched data.
        3. Ensures the price data is 1-dimensional (uses 'Close' price).
        4. Calculates short-term (e.g., 50-day) and long-term (e.g., 200-day) Simple Moving Averages (SMA).
        5. Determines the regime:
           - 'BULL' if the short-term SMA is above the long-term SMA.
           - 'BEAR' if the short-term SMA is below the long-term SMA.
           - 'NEUTRAL' if SMAs cannot be calculated or are very close (optional).
        6. Returns the regime information.

    Dependencies:
        - Requires historical price data for the market index symbol.
        - Relies on `fetch_price_series` utility.

    Configuration Used (from settings.py):
        - `data_provider.MARKET_INDEX_SYMBOL`: The symbol for the market index (e.g., '^NSEI').
        - `agent_settings.market_regime.SHORT_SMA_PERIOD`: Period for the short-term SMA (default 50).
        - `agent_settings.market_regime.LONG_SMA_PERIOD`: Period for the long-term SMA (default 200).

    Returns:
        dict: A dictionary containing the analysis results, including:
            - symbol (str): The input stock symbol (passed through, not used for calculation).
            - verdict (str): The calculated market regime ('BULL', 'BEAR', 'NEUTRAL', 'NO_DATA').
            - confidence (float): Confidence score (currently fixed based on verdict).
            - value (str | None): The calculated market regime string.
            - details (dict): Contains the calculated regime and the market index used.
            - error (str | None): Error message if execution failed.
            - agent_name (str): The name of the agent ('market_regime_agent').
    """
    settings = get_settings()
    market_settings = settings.agent_settings.market_regime
    market_symbol = settings.data_provider.MARKET_INDEX_SYMBOL

    # Fetch market index price data
    try:
        market_prices = await fetch_price_series(market_symbol)
    except Exception as e:
        logger.error(f"[{agent_name}] Failed to fetch market index data for {market_symbol}: {e}")
        return {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {"reason": f"Failed to fetch market index data: {e}"},
            "agent_name": agent_name,
        }

    # Validate and process data
    if market_prices is None or market_prices.empty:
        return {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {"reason": f"No price data available for market index {market_symbol}"},
            "agent_name": agent_name,
        }

    # Ensure market_prices is a pandas Series of closing prices
    if isinstance(market_prices, pd.DataFrame):
        if 'close' in market_prices.columns:
            close_prices = market_prices['close']
        elif 'Close' in market_prices.columns:
            close_prices = market_prices['Close']
        else:
            # Fallback: try to find the first numeric column
            numeric_cols = market_prices.select_dtypes(include=np.number).columns
            if not numeric_cols.empty:
                close_prices = market_prices[numeric_cols[0]]
                logger.warning(f"[{agent_name}] Using first numeric column for market index {market_symbol} as 'close'/'Close' not found.")
            else:
                 return {"symbol": symbol, "verdict": "NO_DATA", "confidence": 0.0, "value": None, "details": {"reason": f"Could not find usable price column in market index data for {market_symbol}"}, "agent_name": agent_name}
    elif isinstance(market_prices, np.ndarray) and market_prices.ndim > 1:
        if market_prices.shape[1] > 3:
            close_prices = pd.Series(market_prices[:, 3]) # Assume 4th column is close
        else:
             return {"symbol": symbol, "verdict": "NO_DATA", "confidence": 0.0, "value": None, "details": {"reason": f"Market index numpy array for {market_symbol} has too few columns."}, "agent_name": agent_name}
    elif isinstance(market_prices, pd.Series):
        close_prices = market_prices
    else:
        try:
            close_prices = pd.Series(market_prices)
        except Exception as e:
             return {"symbol": symbol, "verdict": "NO_DATA", "confidence": 0.0, "value": None, "details": {"reason": f"Could not convert market index data to Series for {market_symbol}: {e}"}, "agent_name": agent_name}

    # Get SMA periods from settings with defaults
    short_period = getattr(market_settings, 'SHORT_SMA_PERIOD', 50)
    long_period = getattr(market_settings, 'LONG_SMA_PERIOD', 200)

    if len(close_prices) < long_period:
        return {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {"reason": f"Insufficient data ({len(close_prices)} points) for longest SMA period ({long_period}) on {market_symbol}"},
            "agent_name": agent_name,
        }

    # Calculate SMAs
    try:
        short_sma = close_prices.rolling(window=short_period).mean().iloc[-1]
        long_sma = close_prices.rolling(window=long_period).mean().iloc[-1]
    except Exception as e:
        logger.error(f"[{agent_name}] Error calculating SMAs for {market_symbol}: {e}")
        return {
            "symbol": symbol,
            "verdict": "ERROR",
            "confidence": 0.0,
            "value": None,
            "details": {"reason": f"Error calculating SMAs: {e}"},
            "agent_name": agent_name,
        }

    # Determine Regime (Simple SMA Crossover)
    if pd.isna(short_sma) or pd.isna(long_sma):
         regime = "NEUTRAL" # Or NO_DATA if preferred
         confidence = 0.3
    elif short_sma > long_sma:
        regime = "BULL"
        confidence = 0.7
    elif short_sma < long_sma:
        regime = "BEAR"
        confidence = 0.7
    else:
        regime = "NEUTRAL"
        confidence = 0.5

    # Return result including the required 'market_regime' in details
    result = {
        "symbol": symbol, # Pass through the original symbol
        "verdict": regime, # Use regime as the main verdict for this agent
        "confidence": confidence,
        "value": regime, # Also use regime as the primary value
        "details": {
            "market_regime": regime, # <<< This is the required key
            "market_index_used": market_symbol,
            "short_sma": round(short_sma, 2) if not pd.isna(short_sma) else None,
            "long_sma": round(long_sma, 2) if not pd.isna(long_sma) else None,
            "config_used": {
                "short_sma_period": short_period,
                "long_sma_period": long_period
            }
        },
        "agent_name": agent_name,
    }

    return result
