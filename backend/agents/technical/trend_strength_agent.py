from backend.agents.technical.base import TechnicalAgent
from backend.utils.data_provider import fetch_ohlcv_series
import numpy as np
from backend.agents.decorators import standard_agent_execution # Import decorator
import json # Import json
from loguru import logger # Import logger
import pandas_ta as ta # Import pandas_ta
from datetime import datetime, date, timedelta # Import date
from dateutil.relativedelta import relativedelta
from backend.utils.cache_utils import get_redis_client # Correct import path
import pandas as pd # Import pandas for type checking

agent_name = "trend_strength_agent"


class TrendStrengthAgent(TechnicalAgent):
    async def _execute(self, symbol: str, agent_outputs: dict) -> dict:
        try:
            # Define date range
            end_date = date.today() # Use date.today()
            start_date = end_date - relativedelta(months=7) # Use relativedelta

            # Fetch OHLCV data with interval
            ohlcv_data = await fetch_ohlcv_series(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                interval='1d' # Added interval
            )
            # Check if fetched data is a valid DataFrame
            if not isinstance(ohlcv_data, pd.DataFrame) or ohlcv_data.empty:
                logger.warning(f"[{agent_name} Class] Insufficient or invalid data for {symbol}. Type: {type(ohlcv_data)}")
                return self._error_response(symbol, f"Insufficient or invalid OHLCV data received. Type: {type(ohlcv_data)}")

            # Ensure data has enough points for calculations
            if len(ohlcv_data) < 50: # Need at least 50 for SMA50
                 logger.warning(f"[{agent_name} Class] Insufficient data points ({len(ohlcv_data)}) for {symbol}.")
                 return self._error_response(symbol, f"Insufficient historical data points ({len(ohlcv_data)} < 50)")

            # Calculate trend metrics
            close = ohlcv_data["close"]
            sma20 = close.rolling(window=20).mean()
            sma50 = close.rolling(window=50).mean()

            # Check if enough data for rolling means
            if sma20.isna().iloc[-1] or sma50.isna().iloc[-1] or len(sma20) < 20 or len(sma50) < 20:
                 return self._error_response(symbol, "Insufficient data for SMA calculation")

            # Directional strength
            direction = 1 if sma20.iloc[-1] > sma50.iloc[-1] else -1
            # Ensure enough points for slope calculation
            if len(sma20) < 20 or len(sma50) < 20:
                 return self._error_response(symbol, "Insufficient data for slope calculation")
            sma20_prev = sma20.iloc[-20] if len(sma20) >= 20 else sma20.iloc[0]
            sma50_prev = sma50.iloc[-20] if len(sma50) >= 20 else sma50.iloc[0]

            slope20 = (sma20.iloc[-1] - sma20_prev) / sma20_prev if sma20_prev != 0 else 0.0
            slope50 = (sma50.iloc[-1] - sma50_prev) / sma50_prev if sma50_prev != 0 else 0.0

            # Volume trend confirmation
            volume = ohlcv_data["volume"]
            if len(volume) < 20:
                 return self._error_response(symbol, "Insufficient data for volume trend")
            vol_sma = volume.rolling(window=20).mean()
            if vol_sma.isna().iloc[-1]:
                 return self._error_response(symbol, "Insufficient data for volume SMA")
            vol_trend = volume.iloc[-1] > vol_sma.iloc[-1]

            # Combine metrics for strength score
            strength_score = abs(slope20) * (1.5 if direction * slope20 > 0 else 0.5)
            if vol_trend and direction * slope20 > 0:
                strength_score *= 1.2

            # Market regime adjustment
            market_context = await self.get_market_context(symbol)
            regime = market_context.get("regime", "NEUTRAL")

            # Determine verdict based on strength and direction
            if strength_score > 0.02:
                verdict = "STRONG_UPTREND" if direction > 0 else "STRONG_DOWNTREND"
                confidence = self.adjust_for_market_regime(0.8, regime)
            elif strength_score > 0.01:
                verdict = "WEAK_UPTREND" if direction > 0 else "WEAK_DOWNTREND"
                confidence = self.adjust_for_market_regime(0.6, regime)
            else:
                verdict = "NO_TREND"
                confidence = 0.4

            return {
                "symbol": symbol,
                "verdict": verdict,
                "confidence": confidence,
                "value": round(strength_score * direction, 4),
                "details": {
                    "strength_score": round(strength_score, 4),
                    "direction": direction,
                    "slope20": round(slope20, 4),
                    "slope50": round(slope50, 4),
                    "volume_confirms": vol_trend,
                    "market_regime": regime,
                },
                "error": None,
                "agent_name": agent_name,
            }

        except Exception as e:
            logger.error(f"Trend strength calculation error: {e}")
            return self._error_response(symbol, str(e))


@standard_agent_execution(agent_name=agent_name, category="technical") # Add agent_name
# Correct signature: agent_outputs is second, period is keyword arg
async def run(symbol: str, agent_outputs: dict = None, period: int = 14) -> dict:
    """
    Calculates the Average Directional Index (ADX) to gauge trend strength.
    DEPRECATED: This function seems to be an older implementation or potentially
    confused with ADX. The TrendStrengthAgent class above provides a more robust
    trend analysis based on SMAs and volume.
    Keeping for reference but recommend using the class-based approach.
    """
    logger.warning("The standalone `run` function in trend_strength_agent.py is potentially deprecated. Consider using TrendStrengthAgent.")
    cache_key = f"{agent_name}:{symbol}:{period}"
    redis_client = await get_redis_client() # Await redis client
    cached_data = await redis_client.get(cache_key)
    # Define date range (e.g., 7 months for daily data)
    end_date = date.today() # Use date.today()
    # Need enough data for ADX calculation (period * 2 + buffer)
    start_date = end_date - timedelta(days=period * 3 + 90) # Generous buffer

    # Fetch OHLCV data with start_date and end_date
    ohlcv_data = await fetch_ohlcv_series(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        interval='1d' # Assuming daily interval is needed
    )

    # Check if fetched data is a valid DataFrame
    if not isinstance(ohlcv_data, pd.DataFrame) or ohlcv_data.empty or len(ohlcv_data) < period * 2:
        logger.warning(f"[{agent_name} standalone] Insufficient or invalid data for {symbol}. Type: {type(ohlcv_data)}")
        return {
            "symbol": symbol,
            "verdict": "NO_DATA",
            "confidence": 0.0,
            "value": None,
            "details": {"reason": f"Insufficient or invalid OHLCV data for ADX. Type: {type(ohlcv_data)}"},
            "agent_name": agent_name,
        }

    try:
        # Placeholder for actual ADX calculation using a library like pandas_ta
        # Example (requires pandas_ta installed):
        # import pandas_ta as ta
        # adx_df = ohlcv_data.ta.adx(length=period)
        # if adx_df is None or adx_df.empty:
        #     raise ValueError("ADX calculation failed")
        # adx_value = adx_df[f'ADX_{period}'].iloc[-1]
        # dmp_value = adx_df[f'DMP_{period}'].iloc[-1]
        # dmn_value = adx_df[f'DMN_{period}'].iloc[-1]

        # *** Replace with actual ADX calculation ***
        adx_value = 25 # Placeholder value
        dmp_value = 30 # Placeholder value
        dmn_value = 20 # Placeholder value
        # *** End Placeholder ***

        if adx_value > 25:
            if dmp_value > dmn_value:
                verdict = "STRONG_UPTREND"
                confidence = min(adx_value / 50, 1.0)
            else:
                verdict = "STRONG_DOWNTREND"
                confidence = min(adx_value / 50, 1.0)
        else:
            verdict = "NO_TREND"
            confidence = 0.5

        return {
            "symbol": symbol,
            "verdict": verdict,
            "confidence": confidence,
            "value": round(adx_value, 2),
            "details": {
                "adx": round(adx_value, 2),
                "dmp": round(dmp_value, 2),
                "dmn": round(dmn_value, 2),
            },
            "agent_name": agent_name,
        }
    except Exception as e:
        logger.error(f"Error calculating ADX for {symbol}: {e}")
        return {
            "symbol": symbol,
            "verdict": "ERROR",
            "confidence": 0.0,
            "value": None,
            "details": {"reason": f"Calculation error: {e}"},
            "agent_name": agent_name,
        }
