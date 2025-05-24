import pandas as pd
import numpy as np
# from backend.utils.data_provider import fetch_price_series # Old import
from backend.utils.data_provider import fetch_ohlcv_series # New: For HLCV data
from backend.agents.decorators import standard_agent_execution
from backend.config.settings import get_settings
from loguru import logger
# from unittest.mock import MagicMock # Import MagicMock for fallback - No longer needed with direct settings access
from backend.agents.technical.utils import compute_atr # New: For ATR calculation

agent_name = "sma_agent"
AGENT_CATEGORY = "technical"

@standard_agent_execution(
    agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=3600
)
async def run(symbol: str, agent_outputs: dict = None) -> dict:
    """
    Calculates Simple Moving Averages (SMA) and generates trading signals with advanced logic.

    Purpose:
        Identifies trends and potential buy/sell signals based on SMA crossovers,
        price relative to SMAs, distance from long SMA (ATR normalized), and volume confirmation.

    Metrics Calculated:
        - Short-term SMA
        - Long-term SMA
        - ATR (Average True Range)
        - Price distance from Long SMA (ATR normalized)
        - Average Volume

    Logic:
        1. Fetches historical OHLCV data.
        2. Calculates SMAs, ATR, and average volume.
        3. Analyzes SMA crossovers (Golden/Death Cross) with volume confirmation.
        4. Evaluates price position relative to SMAs.
        5. Calculates price distance from long SMA, normalized by ATR, for overextension signals.
        6. Considers market regime (from agent_outputs if available) to adjust confidence.
        7. Determines a nuanced verdict (e.g., 'GOLDEN_CROSS_STRONG', 'PRICE_ABOVE_SMAS_OVERSOLD_REVERSION').
        8. Calculates confidence based on the confluence of factors.

    Dependencies:
        - Requires historical OHLCV data (`fetch_ohlcv_series`).
        - `compute_atr` utility.

    Configuration Used (from settings.py -> AgentSettings -> SmaAgentSettings):
        - `SHORT_WINDOW`: Lookback period for the short-term SMA (default 50).
        - `LONG_WINDOW`: Lookback period for the long-term SMA (default 200).
        - `ATR_PERIOD`: Lookback period for ATR (default 14).
        - `VOLUME_AVG_PERIOD`: Lookback period for average volume (default 20).
        - `ATR_DISTANCE_THRESHOLD`: ATR multiples for overextension (default 2.0).

    Return Structure:
        A dictionary containing symbol, verdict, confidence, value (price),
        details (SMAs, ATR, volume info, distance, regime), agent_name, and error.
    """
    settings = get_settings()
    agent_settings = settings.agent_settings
    sma_settings = getattr(agent_settings, "sma", None)

    short_window = getattr(sma_settings, 'SHORT_WINDOW', 50) if sma_settings else 50
    long_window = getattr(sma_settings, 'LONG_WINDOW', 200) if sma_settings else 200
    atr_period = getattr(sma_settings, 'ATR_PERIOD', 14) if sma_settings else 14
    volume_avg_period = getattr(sma_settings, 'VOLUME_AVG_PERIOD', 20) if sma_settings else 20
    atr_distance_threshold = getattr(sma_settings, 'ATR_DISTANCE_THRESHOLD', 2.0) if sma_settings else 2.0

    # Fetch OHLCV data (adjust period based on longest window + buffer)
    fetch_period_days = max(long_window, atr_period, volume_avg_period) + 60 # Increased buffer for all calcs
    
    # Extract market regime and volatility factor from agent_outputs if available
    market_regime = agent_outputs.get("market_context", {}).get("regime", "UNKNOWN") if agent_outputs else "UNKNOWN"
    # volatility_factor = agent_outputs.get("market_context", {}).get("volatility_factor", 1.0) if agent_outputs else 1.0

    ohlcv_data = await fetch_ohlcv_series(symbol, start_date=(pd.Timestamp.now().date() - pd.Timedelta(days=fetch_period_days)), end_date=pd.Timestamp.now().date(), interval='1d')

    if ohlcv_data is None or ohlcv_data.empty or len(ohlcv_data) < max(long_window, atr_period, volume_avg_period):
        reason = f"Insufficient OHLCV data (need at least {max(long_window, atr_period, volume_avg_period)} days, got {len(ohlcv_data) if ohlcv_data is not None else 0})"
        logger.warning(f"[{agent_name}] {reason} for {symbol}")
        return {
            "symbol": symbol, "verdict": "NO_DATA", "confidence": 0.0, "value": None,
            "details": {"reason": reason, "market_regime": market_regime}, "agent_name": agent_name,
        }

    # Ensure required columns exist
    required_cols = ['high', 'low', 'close', 'volume']
    if not all(col in ohlcv_data.columns for col in required_cols):
        logger.error(f"[{agent_name}] Missing one or more required columns (high, low, close, volume) in OHLCV data for {symbol}.")
        return {
            "symbol": symbol, "verdict": "INVALID_DATA", "confidence": 0.0, "value": None,
            "details": {"reason": "Missing OHLCV columns", "market_regime": market_regime}, "agent_name": agent_name,
        }

    prices = ohlcv_data['close']
    high_prices = ohlcv_data['high']
    low_prices = ohlcv_data['low']
    volume_data = ohlcv_data['volume']

    try:
        short_sma = prices.rolling(window=short_window).mean()
        long_sma = prices.rolling(window=long_window).mean()
        atr = compute_atr(high_prices, low_prices, prices, atr_period)
        avg_volume = volume_data.rolling(window=volume_avg_period).mean().iloc[-1]
    except Exception as e:
        logger.error(f"[{agent_name}] Error calculating indicators for {symbol}: {e}", exc_info=True)
        return {
            "symbol": symbol, "verdict": "ERROR", "confidence": 0.0, "value": None,
            "details": {"reason": f"Error during indicator calculation: {e}", "market_regime": market_regime}, 
            "agent_name": agent_name,
        }

    if len(prices) < 1 or short_sma.dropna().empty or long_sma.dropna().empty or pd.isna(atr) or pd.isna(avg_volume):
         reason = "Not enough data points after indicator calculation or NaN ATR/Volume."
         logger.warning(f"[{agent_name}] {reason} for {symbol}. ATR: {atr}, AvgVol: {avg_volume}")
         return {
            "symbol": symbol, "verdict": "INVALID_DATA", "confidence": 0.0, "value": None,
            "details": {"reason": reason, "market_regime": market_regime}, "agent_name": agent_name,
        }

    latest_price = prices.iloc[-1]
    latest_short_sma = short_sma.iloc[-1]
    latest_long_sma = long_sma.iloc[-1]
    latest_volume = volume_data.iloc[-1]

    if pd.isna(latest_price) or pd.isna(latest_short_sma) or pd.isna(latest_long_sma):
         reason = f"NaN values in latest price/SMAs (Price: {latest_price}, SMA{short_window}: {latest_short_sma}, SMA{long_window}: {latest_long_sma})"
         logger.warning(f"[{agent_name}] {reason} for {symbol}")
         return {
            "symbol": symbol, "verdict": "INVALID_DATA", "confidence": 0.0, "value": None,
            "details": {"reason": reason, "market_regime": market_regime}, "agent_name": agent_name,
        }

    verdict = "HOLD_NEUTRAL"
    base_signal_strength = 0.5 # 0.0 (strong sell) to 1.0 (strong buy)
    volume_confirms = False

    # 1. Crossover Logic with Volume Confirmation
    can_check_crossover = len(short_sma.dropna()) >= 2 and len(long_sma.dropna()) >= 2
    if can_check_crossover:
        prev_short_sma = short_sma.iloc[-2]
        prev_long_sma = long_sma.iloc[-2]
        if not pd.isna(prev_short_sma) and not pd.isna(prev_long_sma):
            volume_confirms = latest_volume > avg_volume * 1.2 # Example: 20% above average
            
            if latest_short_sma > latest_long_sma and prev_short_sma <= prev_long_sma: # Golden Cross
                verdict = "GOLDEN_CROSS_BULLISH"
                base_signal_strength = 0.75
                if volume_confirms: 
                    verdict += "_VOL_CONF"
                    base_signal_strength = min(1.0, base_signal_strength + 0.15)
            elif latest_short_sma < latest_long_sma and prev_short_sma >= prev_long_sma: # Death Cross
                verdict = "DEATH_CROSS_BEARISH"
                base_signal_strength = 0.25
                if volume_confirms:
                    verdict += "_VOL_CONF"
                    base_signal_strength = max(0.0, base_signal_strength - 0.15)

    # 2. Price Relative to SMAs & ATR-Normalized Distance from Long SMA
    price_dist_from_long_sma_atr = (latest_price - latest_long_sma) / atr if atr > 0 else 0

    if verdict == "HOLD_NEUTRAL": # Only if no crossover detected
        is_bullish_sma_order = latest_short_sma > latest_long_sma
        is_bearish_sma_order = latest_short_sma < latest_long_sma

        if latest_price > latest_short_sma and latest_price > latest_long_sma: # Price above both SMAs
            verdict = "PRICE_ABOVE_SMAS_BULLISH"
            base_signal_strength = 0.65 if is_bullish_sma_order else 0.60
            if price_dist_from_long_sma_atr > atr_distance_threshold: # Overextended?
                verdict = "PRICE_ABOVE_SMAS_OVEREXTENDED_BEARISH_REVERSION"
                base_signal_strength = 0.35 # Potential reversion signal
        elif latest_price < latest_short_sma and latest_price < latest_long_sma: # Price below both SMAs
            verdict = "PRICE_BELOW_SMAS_BEARISH"
            base_signal_strength = 0.35 if is_bearish_sma_order else 0.40
            if price_dist_from_long_sma_atr < -atr_distance_threshold: # Oversold?
                verdict = "PRICE_BELOW_SMAS_OVEREXTENDED_BULLISH_REVERSION"
                base_signal_strength = 0.65 # Potential reversion signal
        elif (is_bullish_sma_order and latest_price > latest_long_sma and latest_price < latest_short_sma) or \
             (is_bearish_sma_order and latest_price < latest_long_sma and latest_price > latest_short_sma):
             verdict = "PRICE_BETWEEN_SMAS_NEUTRAL"
             base_signal_strength = 0.5
    
    # 3. Calibrated Confidence Score based on Market Regime
    final_confidence = base_signal_strength
    if market_regime == "BULL":
        if final_confidence > 0.5: final_confidence = min(1.0, final_confidence + 0.1)
        else: final_confidence = final_confidence + (0.5 - final_confidence) * 0.2 # Weaken bearish in bull
    elif market_regime == "BEAR":
        if final_confidence < 0.5: final_confidence = max(0.0, final_confidence - 0.1)
        else: final_confidence = final_confidence - (final_confidence - 0.5) * 0.2 # Weaken bullish in bear
    # Sideways/Unknown market regime doesn't strongly adjust base signal strength here

    details = {
        f"sma_{short_window}": round(latest_short_sma, 4),
        f"sma_{long_window}": round(latest_long_sma, 4),
        "short_window": short_window,
        "long_window": long_window,
        "atr": round(atr, 4) if not pd.isna(atr) else None,
        "atr_period": atr_period,
        "avg_volume": round(avg_volume, 0) if not pd.isna(avg_volume) else None,
        "latest_volume": round(latest_volume, 0),
        "volume_confirms_crossover": volume_confirms,
        "price_dist_from_long_sma_atr": round(price_dist_from_long_sma_atr, 2),
        "atr_distance_threshold": atr_distance_threshold,
        "market_regime_used": market_regime
    }
    if can_check_crossover and not (pd.isna(prev_short_sma) or pd.isna(prev_long_sma)):
        details[f"prev_sma_{short_window}"] = round(prev_short_sma, 4)
        details[f"prev_sma_{long_window}"] = round(prev_long_sma, 4)

    return {
        "symbol": symbol,
        "verdict": verdict,
        "confidence": round(final_confidence, 4),
        "value": round(latest_price, 4),
        "details": details,
        "agent_name": agent_name,
    }

