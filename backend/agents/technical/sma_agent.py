import pandas as pd
import numpy as np
from backend.utils.data_provider import fetch_price_series
from backend.agents.decorators import standard_agent_execution
from backend.config.settings import get_settings
from loguru import logger
from unittest.mock import MagicMock # Import MagicMock for fallback

agent_name = "sma_agent"
AGENT_CATEGORY = "technical"

@standard_agent_execution(
    agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=3600
)
async def run(symbol: str, agent_outputs: dict = None) -> dict:
    """
    Calculates Simple Moving Averages (SMA) and generates trading signals.

    Purpose:
        Identifies trends and potential buy/sell signals based on the relationship
        between short-term and long-term SMAs, and the current price relative to the SMAs.
        Common signals include Golden Cross (short SMA crosses above long SMA) and
        Death Cross (short SMA crosses below long SMA).

    Metrics Calculated:
        - Short-term SMA (e.g., 50-day)
        - Long-term SMA (e.g., 200-day)

    Logic:
        1. Fetches historical price series for the stock symbol.
        2. Calculates the short-term and long-term SMAs based on configured window sizes.
        3. Compares the latest short SMA, long SMA, and closing price.
        4. Determines a verdict:
            - 'GOLDEN_CROSS': Short SMA just crossed above Long SMA.
            - 'DEATH_CROSS': Short SMA just crossed below Long SMA.
            - 'PRICE_ABOVE_SMAS': Price is above both SMAs (bullish).
            - 'PRICE_BELOW_SMAS': Price is below both SMAs (bearish).
            - 'PRICE_BETWEEN_SMAS': Price is between the SMAs (neutral/transition).
            - 'HOLD': Default if no other specific condition is met strongly.
        5. Calculates confidence based on the strength/clarity of the signal.

    Dependencies:
        - Requires historical price data (`fetch_price_series`).

    Configuration Used (from settings.py -> AgentSettings -> SmaAgentSettings):
        - `SHORT_WINDOW`: Lookback period for the short-term SMA (default 50).
        - `LONG_WINDOW`: Lookback period for the long-term SMA (default 200).

    Return Structure:
        A dictionary containing:
        - symbol (str): The stock symbol.
        - verdict (str): Trading signal (e.g., 'GOLDEN_CROSS', 'PRICE_ABOVE_SMAS').
        - confidence (float): Confidence score (0.0 to 1.0).
        - value (float | None): The latest closing price.
        - details (dict): Contains short SMA, long SMA, and potentially crossover info.
        - agent_name (str): The name of this agent.
        - error (str | None): Error message if an issue occurred.
    """
    settings = get_settings()
    # Ensure sma settings exist in the config structure or provide defaults
    # Use getattr for safe access to potentially missing 'sma' attribute
    agent_settings = settings.agent_settings
    sma_settings = getattr(agent_settings, "sma", None) # Get the nested sma settings object

    # Access attributes on the sma_settings object, providing defaults if it's None or lacks the attribute
    short_window = getattr(sma_settings, 'SHORT_WINDOW', 50) if sma_settings else 50
    long_window = getattr(sma_settings, 'LONG_WINDOW', 200) if sma_settings else 200

    # Fetch price series (adjust period based on longest window + buffer)
    # Need at least long_window periods + 1 previous period for crossover check
    fetch_period_days = long_window + 5
    prices = await fetch_price_series(symbol, period=f"{fetch_period_days}d")

    if prices is None or prices.empty or len(prices) < long_window:
        reason = f"Insufficient price data (need at least {long_window} days, got {len(prices) if prices is not None else 0})"
        logger.warning(f"[{agent_name}] {reason} for {symbol}")
        return {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {"reason": reason},
            "agent_name": agent_name,
        }

    # Ensure prices is a pandas Series (handle potential DataFrame input)
    if isinstance(prices, pd.DataFrame):
         if 'close' in prices.columns:
             prices = prices['close']
         elif not prices.empty:
             # Assuming the first column is the price if 'close' not found
             prices = prices.iloc[:, 0]
         else:
             # Handle empty DataFrame case after type check
             return {
                 "symbol": symbol, "verdict": "NO_DATA", "confidence": 0.0, "value": None,
                 "details": {"reason": "Received empty DataFrame for prices"}, "agent_name": agent_name,
             }

    # Calculate SMAs
    try:
        short_sma = prices.rolling(window=short_window).mean()
        long_sma = prices.rolling(window=long_window).mean()
    except Exception as e:
        logger.error(f"[{agent_name}] Error calculating SMAs for {symbol}: {e}")
        return {
            "symbol": symbol, "verdict": "ERROR", "confidence": 0.0, "value": None,
            "details": {"reason": f"Error during SMA calculation: {e}"}, "agent_name": agent_name,
        }

    # Get latest values
    # Ensure index is large enough before accessing iloc[-1], iloc[-2]
    if len(prices) < 1 or len(short_sma.dropna()) < 1 or len(long_sma.dropna()) < 1:
         return {
            "symbol": symbol, "verdict": "INVALID_DATA", "confidence": 0.0, "value": None,
            "details": {"reason": "Not enough data points after SMA calculation"}, "agent_name": agent_name,
        }

    latest_price = prices.iloc[-1]
    latest_short_sma = short_sma.iloc[-1]
    latest_long_sma = long_sma.iloc[-1]

    # Check for NaN values (can happen if not enough data despite initial check)
    if pd.isna(latest_price) or pd.isna(latest_short_sma) or pd.isna(latest_long_sma):
         reason = f"NaN values encountered (Price: {latest_price}, SMA{short_window}: {latest_short_sma}, SMA{long_window}: {latest_long_sma})"
         logger.warning(f"[{agent_name}] {reason} for {symbol}")
         return {
            "symbol": symbol,
            "verdict": "INVALID_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {"reason": reason},
            "agent_name": agent_name,
        }

    # Determine Verdict
    verdict = "HOLD" # Default
    confidence = 0.5 # Default

    # Check for crossovers (requires previous day's data)
    # Ensure index is large enough for iloc[-2] and values are not NaN
    can_check_crossover = len(short_sma.dropna()) >= 2 and len(long_sma.dropna()) >= 2

    if can_check_crossover:
        prev_short_sma = short_sma.iloc[-2]
        prev_long_sma = long_sma.iloc[-2]

        # Check if previous values are valid numbers
        if not pd.isna(prev_short_sma) and not pd.isna(prev_long_sma):
            # Golden Cross
            if latest_short_sma > latest_long_sma and prev_short_sma <= prev_long_sma:
                verdict = "GOLDEN_CROSS"
                confidence = 0.9
            # Death Cross
            elif latest_short_sma < latest_long_sma and prev_short_sma >= prev_long_sma:
                verdict = "DEATH_CROSS"
                confidence = 0.9

    # If no crossover detected or not enough data for crossover, check price relative to SMAs
    if verdict == "HOLD":
        is_bullish_sma_order = latest_short_sma > latest_long_sma
        is_bearish_sma_order = latest_short_sma < latest_long_sma

        if latest_price > latest_short_sma and latest_price > latest_long_sma:
             verdict = "PRICE_ABOVE_SMAS"
             confidence = 0.75 if is_bullish_sma_order else 0.65 # Higher confidence if SMAs align
        elif latest_price < latest_short_sma and latest_price < latest_long_sma:
             verdict = "PRICE_BELOW_SMAS"
             confidence = 0.75 if is_bearish_sma_order else 0.65 # Higher confidence if SMAs align
        # Price between SMAs is more ambiguous
        elif (is_bullish_sma_order and latest_price > latest_long_sma and latest_price < latest_short_sma) or \
             (is_bearish_sma_order and latest_price < latest_long_sma and latest_price > latest_short_sma):
             verdict = "PRICE_BETWEEN_SMAS"
             confidence = 0.5
        # Handle cases where price is outside but SMAs are crossed (e.g., price > short > long)
        # These were covered by PRICE_ABOVE/BELOW_SMAS, so HOLD remains if none match

    return {
        "symbol": symbol,
        "verdict": verdict,
        "confidence": round(confidence, 4),
        "value": round(latest_price, 4),
        "details": {
            f"sma_{short_window}": round(latest_short_sma, 4),
            f"sma_{long_window}": round(latest_long_sma, 4),
            "short_window": short_window,
            "long_window": long_window,
        },
        "agent_name": agent_name,
    }

