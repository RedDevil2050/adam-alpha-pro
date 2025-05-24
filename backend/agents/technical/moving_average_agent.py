import pandas as pd
import numpy as np # Added for np.abs and np.nan if needed
from backend.utils.data_provider import fetch_ohlcv_series
# from backend.utils.cache_utils import get_redis_client # Not used with standard_agent_execution
from backend.agents.technical.utils import tracker, compute_atr # Import compute_atr
from datetime import datetime, date, timedelta 
# from dateutil.relativedelta import relativedelta # Not strictly needed for this logic
from backend.agents.decorators import standard_agent_execution 
# import json # Not directly used for caching with decorator
from loguru import logger 
from backend.config.settings import get_settings # For agent-specific settings

agent_name = "moving_average_agent"
AGENT_CATEGORY = "technical"

@standard_agent_execution(agent_name=agent_name, category=AGENT_CATEGORY, cache_ttl=3600)
async def run(symbol: str, agent_outputs: dict = None, window: int = None) -> dict: # window can be from settings
    """
    Calculates Moving Average characteristics and generates trading signals with advanced logic.

    Purpose:
        Identifies trend direction and strength based on MA slope/velocity,
        price position relative to MA, and volume confirmation.

    Metrics Calculated:
        - Moving Average (SMA or EMA based on config)
        - MA Slope (percentage change)
        - MA Velocity (change over N periods)
        - ATR (Average True Range)
        - Average Volume

    Logic:
        1. Fetches historical OHLCV data.
        2. Calculates the MA, its slope, velocity, ATR, and average volume.
        3. Evaluates price position relative to the MA.
        4. Confirms signals (e.g., MA break) with volume.
        5. Considers market regime (from agent_outputs) to adjust confidence.
        6. Determines a nuanced verdict (e.g., 'STRONG_UPTREND_ACCELERATING', 'PRICE_BREAK_MA_VOL_CONF').
        7. Calculates confidence based on the confluence of factors.

    Dependencies:
        - Requires historical OHLCV data (`fetch_ohlcv_series`).
        - `compute_atr` utility.

    Configuration Used (from settings.py -> AgentSettings -> MovingAverageAgentSettings):
        - `WINDOW`: Lookback period for the MA (default 20).
        - `MA_TYPE`: 'SMA' or 'EMA' (default 'SMA').
        - `SLOPE_PERIOD`: Period for MA slope calculation (default 1, i.e., vs prev value).
        - `VELOCITY_PERIOD`: Period for MA velocity calculation (default 5).
        - `ATR_PERIOD`: Lookback period for ATR (default 14).
        - `VOLUME_AVG_PERIOD`: Lookback period for average volume (default 20).

    Return Structure:
        A dictionary containing symbol, verdict, confidence, value (MA slope pct),
        details (MA value, slope, velocity, ATR, volume, regime), agent_name, and error.
    """
    settings = get_settings()
    agent_settings = settings.agent_settings
    ma_settings = getattr(agent_settings, "moving_average", None) # Assuming settings key is "moving_average"

    # Use provided window if available, else from settings, else default
    window = window if window is not None else (getattr(ma_settings, 'WINDOW', 20) if ma_settings else 20)
    ma_type = getattr(ma_settings, 'MA_TYPE', 'SMA') if ma_settings else 'SMA'
    slope_period = getattr(ma_settings, 'SLOPE_PERIOD', 1) if ma_settings else 1 # For slope vs N periods ago
    velocity_period = getattr(ma_settings, 'VELOCITY_PERIOD', 5) if ma_settings else 5 # For MA change over 5 periods
    atr_period = getattr(ma_settings, 'ATR_PERIOD', 14) if ma_settings else 14
    volume_avg_period = getattr(ma_settings, 'VOLUME_AVG_PERIOD', 20) if ma_settings else 20

    # Extract market regime from agent_outputs if available
    market_regime = agent_outputs.get("market_context", {}).get("regime", "UNKNOWN") if agent_outputs else "UNKNOWN"

    # Define date range
    end_date = date.today() 
    # Calculate start date based on max window size + buffer for calculation
    required_data_days = max(window, atr_period, volume_avg_period, velocity_period) + slope_period + 60
    start_date = end_date - timedelta(days=required_data_days) 

    ohlcv_data = await fetch_ohlcv_series(
        symbol=symbol, start_date=start_date, end_date=end_date, interval='1d'
    )

    if not isinstance(ohlcv_data, pd.DataFrame) or ohlcv_data.empty or len(ohlcv_data) < max(window + slope_period, velocity_period + slope_period, atr_period, volume_avg_period):
        reason = f"Insufficient OHLCV data. Need enough for MA({window})+Slope({slope_period}) and other indicators."
        logger.warning(f"[{agent_name}] {reason} for {symbol}. Got {len(ohlcv_data) if ohlcv_data is not None else 0} days.")
        return {
            "symbol": symbol, "verdict": "NO_DATA", "confidence": 0.0, "value": None,
            "details": {"reason": reason, "market_regime": market_regime}, "agent_name": agent_name,
        }

    required_cols = ['high', 'low', 'close', 'volume']
    if not all(col in ohlcv_data.columns for col in required_cols):
        logger.error(f"[{agent_name}] Missing one or more required columns (high, low, close, volume) for {symbol}.")
        return {
            "symbol": symbol, "verdict": "INVALID_DATA", "confidence": 0.0, "value": None,
            "details": {"reason": "Missing OHLCV columns", "market_regime": market_regime}, "agent_name": agent_name,
        }

    close_prices = ohlcv_data["close"]
    high_prices = ohlcv_data['high']
    low_prices = ohlcv_data['low']
    volume_data = ohlcv_data['volume']

    try:
        if ma_type.upper() == 'EMA':
            ma_series = close_prices.ewm(span=window, adjust=False, min_periods=window).mean()
        else: # Default to SMA
            ma_series = close_prices.rolling(window=window, min_periods=window).mean()
        
        atr = compute_atr(high_prices, low_prices, close_prices, atr_period)
        avg_volume = volume_data.rolling(window=volume_avg_period).mean().iloc[-1]
    except Exception as e:
        logger.error(f"[{agent_name}] Error calculating indicators for {symbol}: {e}", exc_info=True)
        return {
            "symbol": symbol, "verdict": "ERROR", "confidence": 0.0, "value": None,
            "details": {"reason": f"Error during indicator calculation: {e}", "market_regime": market_regime},
            "agent_name": agent_name,
        }

    if ma_series.dropna().empty or len(ma_series.dropna()) < slope_period + 1 or len(ma_series.dropna()) < velocity_period +1 or pd.isna(atr) or pd.isna(avg_volume):
        reason = "Not enough data points after MA/ATR/Volume calculation for slope/velocity."
        logger.warning(f"[{agent_name}] {reason} for {symbol}. MA dropna len: {len(ma_series.dropna())}")
        return {
            "symbol": symbol, "verdict": "INVALID_DATA", "confidence": 0.0, "value": None,
            "details": {"reason": reason, "market_regime": market_regime}, "agent_name": agent_name,
        }

    ma_last = ma_series.iloc[-1]
    ma_prev_slope = ma_series.iloc[-1 - slope_period]
    ma_prev_velocity = ma_series.iloc[-1 - velocity_period]
    latest_price = close_prices.iloc[-1]
    latest_volume = volume_data.iloc[-1]

    if pd.isna(ma_last) or pd.isna(ma_prev_slope) or pd.isna(ma_prev_velocity) or pd.isna(latest_price):
        reason = "NaN values in latest MA/price data needed for slope/velocity."
        logger.warning(f"[{agent_name}] {reason} for {symbol}")
        return {
            "symbol": symbol, "verdict": "INVALID_DATA", "confidence": 0.0, "value": None,
            "details": {"reason": reason, "market_regime": market_regime}, "agent_name": agent_name,
        }

    slope_pct = (ma_last - ma_prev_slope) / ma_prev_slope * 100 if ma_prev_slope != 0 else 0.0
    # Velocity as absolute change or percentage change over its period
    velocity_abs = ma_last - ma_prev_velocity 
    # velocity_pct = (ma_last - ma_prev_velocity) / ma_prev_velocity * 100 if ma_prev_velocity != 0 else 0.0

    verdict = "HOLD_NEUTRAL"
    base_signal_strength = 0.5 # 0.0 (strong sell) to 1.0 (strong buy)
    volume_confirms_break = False

    # 1. MA Slope & Velocity Analysis
    # Normalize slope_pct and velocity_abs to a 0-1 range for easier combination if needed
    # For simplicity, we'll use thresholds here.
    strong_slope_threshold = 0.2 # e.g. 0.2% change over slope_period
    strong_velocity_threshold_atr = 0.1 * atr if atr > 0 else 0.05 * ma_last # e.g. MA moved 10% of ATR over velocity_period

    if slope_pct > strong_slope_threshold:
        verdict = "UPTREND_STRONG_SLOPE"
        base_signal_strength = 0.70
        if velocity_abs > strong_velocity_threshold_atr:
            verdict = "UPTREND_ACCELERATING"
            base_signal_strength = 0.80
    elif slope_pct < -strong_slope_threshold:
        verdict = "DOWNTREND_STRONG_SLOPE"
        base_signal_strength = 0.30
        if velocity_abs < -strong_velocity_threshold_atr:
            verdict = "DOWNTREND_ACCELERATING"
            base_signal_strength = 0.20
    
    # 2. Price vs. MA with Volume Confirmation
    price_crossed_above_ma = close_prices.iloc[-2] <= ma_series.iloc[-2] and latest_price > ma_last
    price_crossed_below_ma = close_prices.iloc[-2] >= ma_series.iloc[-2] and latest_price < ma_last
    volume_confirms_break = latest_volume > avg_volume * 1.3 # Example: 30% above average for break confirmation

    if price_crossed_above_ma:
        verdict = "PRICE_BREAK_ABOVE_MA"
        base_signal_strength = 0.65
        if volume_confirms_break:
            verdict += "_VOL_CONF"
            base_signal_strength = 0.75
    elif price_crossed_below_ma:
        verdict = "PRICE_BREAK_BELOW_MA"
        base_signal_strength = 0.35
        if volume_confirms_break:
            verdict += "_VOL_CONF"
            base_signal_strength = 0.25
    elif verdict == "HOLD_NEUTRAL": # If no strong trend and no break, check position
        if latest_price > ma_last:
            verdict = "PRICE_ABOVE_MA_HOLD"
            base_signal_strength = 0.55
        elif latest_price < ma_last:
            verdict = "PRICE_BELOW_MA_HOLD"
            base_signal_strength = 0.45

    # 3. Calibrated Confidence Score based on Market Regime
    final_confidence = base_signal_strength
    if market_regime == "BULL":
        if final_confidence > 0.5: final_confidence = min(1.0, final_confidence + 0.1)
        else: final_confidence = final_confidence + (0.5 - final_confidence) * 0.2 # Weaken bearish in bull
    elif market_regime == "BEAR":
        if final_confidence < 0.5: final_confidence = max(0.0, final_confidence - 0.1)
        else: final_confidence = final_confidence - (final_confidence - 0.5) * 0.2 # Weaken bullish in bear

    details = {
        "ma_type": ma_type,
        "ma_window": window,
        "ma_value": round(ma_last, 4),
        "ma_slope_pct": round(slope_pct, 4),
        "ma_slope_period": slope_period,
        "ma_velocity_abs": round(velocity_abs, 4),
        # "ma_velocity_pct": round(velocity_pct, 4),
        "ma_velocity_period": velocity_period,
        "atr": round(atr, 4) if not pd.isna(atr) else None,
        "atr_period": atr_period,
        "avg_volume": round(avg_volume, 0) if not pd.isna(avg_volume) else None,
        "latest_volume": round(latest_volume, 0),
        "volume_confirms_break": volume_confirms_break,
        "market_regime_used": market_regime
    }

    return {
        "symbol": symbol,
        "verdict": verdict,
        "confidence": round(final_confidence, 4),
        "value": round(slope_pct, 4), # Primary value could be slope or MA value itself
        "details": details,
        "agent_name": agent_name,
    }
