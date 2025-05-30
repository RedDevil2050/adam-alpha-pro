from backend.agents.base.category_bases import TechnicalAgentBase
from backend.models.common_models import VerdictType, MarketRegime
from backend.config.settings import AgentSettings # For type hinting in run fn
from backend.data.providers.base_provider import BaseDataProvider # For type hinting in run fn

from datetime import datetime, timedelta
from loguru import logger # Keep for the run function if it uses it directly
from typing import Any, Dict
import numpy as np # Added for np.nan

AGENT_NAME = "stochastic_oscillator_agent"


class StochasticOscillatorAgent(TechnicalAgentBase):
    # __init__ is inherited from TechnicalAgentBase, which inherits from AgentBase.
    # AgentBase.__init__(self, name, settings, logger, cache_client, data_provider, market_context_provider, **kwargs)
    # will be called.

    async def execute(self, symbol: str, agent_outputs: Dict = None, k_period: int = 14, d_period: int = 3, smoothing: int = 3) -> Dict:
        """
        Executes the agent's logic by calling the base class execute method, 
        which handles caching, calling _execute, and formatting the output.
        Specific parameters for this agent (k_period, d_period, smoothing) are passed as kwargs.
        """
        agent_outputs = agent_outputs or {}
        # self.logger.debug(f"[{self.name}] Forwarding execution to AgentBase for {symbol} with k={k_period}, d={d_period}, s={smoothing}")
        return await super().execute(symbol=symbol,
                                     agent_outputs=agent_outputs,
                                     k_period=k_period,
                                     d_period=d_period,
                                     smoothing=smoothing)

    async def _execute(self, symbol: str, agent_outputs: Dict, k_period: int = 14, d_period: int = 3, smoothing: int = 3) -> Dict:
        """
        Core logic for the Stochastic Oscillator Agent.
        This method is called by AgentBase.execute after cache checks.
        It should return a dictionary with "verdict", "confidence", and "details".
        """
        try:
            market_context_data = await self.get_market_context(symbol)
            raw_regime_value_from_context = str(market_context_data.get("regime", MarketRegime.UNKNOWN.value)).upper()
            volatility_factor = market_context_data.get("volatility_factor", 1.0)
            
            self.logger.debug(f"[{self.name}] _execute for {symbol}. Market context: Regime='{raw_regime_value_from_context}', VolatilityFactor={volatility_factor}")

            current_params = {"k": int(k_period), "d": int(d_period), "s": int(smoothing)} # Ensure standard int types

            if not self.data_provider:
                 self.logger.error(f"[{self.name}] Data provider not initialized for {symbol}.")
                 # Corrected _error_response call
                 return self._error_response(
                     error_message="Data provider not available.",
                     details={"params": current_params, "symbol": symbol}
                 )

            end_date = datetime.now().date()
            required_data_points = (k_period - 1) + (smoothing - 1) + (d_period - 1) + 2
            start_date = end_date - timedelta(days=required_data_points + 60) # Buffer

            df = await self.data_provider.fetch_ohlcv_series(symbol, start_date=start_date, end_date=end_date, interval='1d')

            if df is None or df.empty or len(df) < required_data_points:
                msg = f"Insufficient OHLCV data (need {required_data_points}, got {len(df) if df is not None else 0})"
                self.logger.warning(f"[{self.name}] {msg} for {symbol}.")
                # Corrected _error_response call
                return self._error_response(
                    error_message=msg,
                    details={"params": current_params, "market_regime": raw_regime_value_from_context, "symbol": symbol}
                )

            if not all(col in df.columns for col in ['high', 'low', 'close']):
                msg = "Missing required OHLC columns in data."
                self.logger.error(f"[{self.name}] {msg} for {symbol}.")
                # Corrected _error_response call
                return self._error_response(
                    error_message=msg,
                    details={"params": current_params, "market_regime": raw_regime_value_from_context, "symbol": symbol}
                )

            df_copy = df.copy()
            df_copy.loc[:, 'low_min'] = df_copy["low"].rolling(window=k_period, min_periods=k_period).min()
            df_copy.loc[:, 'high_max'] = df_copy["high"].rolling(window=k_period, min_periods=k_period).max()
            
            denominator = df_copy['high_max'] - df_copy['low_min']
            df_copy.loc[:, 'fast_k'] = 100 * ((df_copy["close"] - df_copy['low_min']) / denominator.replace(0, np.nan))
            df_copy.loc[:, 'fast_k'] = df_copy['fast_k'].fillna(50)

            df_copy.loc[:, 'k_series'] = df_copy['fast_k'].rolling(window=smoothing, min_periods=smoothing).mean()
            df_copy.loc[:, 'd_series'] = df_copy['k_series'].rolling(window=d_period, min_periods=d_period).mean()

            if df_copy['k_series'].iloc[-2:].isna().any() or df_copy['d_series'].iloc[-2:].isna().any():
                msg = "NaN values in k_series or d_series. Could not calculate K/D series."
                self.logger.warning(f"[{self.name}] {msg} for {symbol}.")
                # Corrected _error_response call
                return self._error_response(
                    error_message=msg,
                    details={"params": current_params, "market_regime": raw_regime_value_from_context, "symbol": symbol}
                )
                
            latest_k, latest_d = df_copy['k_series'].iloc[-1], df_copy['d_series'].iloc[-1]
            prev_k, prev_d = df_copy['k_series'].iloc[-2], df_copy['d_series'].iloc[-2]

            stoch_settings = self.settings.stochastic_oscillator if hasattr(self.settings, 'stochastic_oscillator') else {}
            base_oversold = stoch_settings.get("oversold_threshold", 20)
            base_overbought = stoch_settings.get("overbought_threshold", 80)
            
            oversold_threshold = float(base_oversold)
            overbought_threshold = float(base_overbought)

            bull_adjustment = stoch_settings.get("bull_market_oversold_adjustment", 5)
            bear_adjustment = stoch_settings.get("bear_market_oversold_adjustment", -5)
            volatility_sensitivity = stoch_settings.get("volatility_threshold_sensitivity", 0.2)

            if raw_regime_value_from_context == MarketRegime.BULL.value.upper():
                oversold_threshold += bull_adjustment
            elif raw_regime_value_from_context == MarketRegime.BEAR.value.upper():
                 oversold_threshold += bear_adjustment
            
            if volatility_factor != 1.0:
                threshold_range_adjustment = (overbought_threshold - oversold_threshold) * (volatility_factor - 1.0) * volatility_sensitivity
                oversold_threshold -= threshold_range_adjustment / 2
                overbought_threshold += threshold_range_adjustment / 2
            
            oversold_threshold = max(5.0, min(40.0, oversold_threshold))
            overbought_threshold = min(95.0, max(60.0, overbought_threshold))
            
            verdict_str = VerdictType.HOLD_NEUTRAL.value 
            base_signal_strength = 0.5

            # Crossover logic
            if prev_k <= prev_d and latest_k > latest_d:
                if latest_k < oversold_threshold + 10 :
                    verdict_str = VerdictType.BUY_OVERSOLD_CROSS.value
                    base_signal_strength = 0.75
                else:
                    verdict_str = VerdictType.BUY.value 
                    base_signal_strength = 0.65
            elif prev_k >= prev_d and latest_k < latest_d:
                if latest_k > overbought_threshold - 10:
                    verdict_str = VerdictType.SELL_OVERBOUGHT_CROSS.value
                    base_signal_strength = 0.25
                else:
                    verdict_str = VerdictType.SELL.value
                    base_signal_strength = 0.35
            
            final_confidence = base_signal_strength
            
            # Regime-based confidence adjustment
            bull_bull_confidence_boost = stoch_settings.get("bull_market_bullish_signal_boost", 0.1)
            bull_bear_confidence_dampen_factor = stoch_settings.get("bull_market_bearish_signal_dampen_factor", 0.8)
            bear_bear_confidence_boost = stoch_settings.get("bear_market_bearish_signal_boost", 0.1)
            bear_bull_confidence_dampen_factor = stoch_settings.get("bear_market_bullish_signal_dampen_factor", 0.8)

            if verdict_str in [VerdictType.BUY.value, VerdictType.BUY_OVERSOLD_CROSS.value]:
                if raw_regime_value_from_context == MarketRegime.BULL.value.upper():
                    final_confidence = min(1.0, final_confidence + bull_bull_confidence_boost)
                elif raw_regime_value_from_context == MarketRegime.BEAR.value.upper():
                    final_confidence *= bear_bull_confidence_dampen_factor 
            elif verdict_str in [VerdictType.SELL.value, VerdictType.SELL_OVERBOUGHT_CROSS.value]:
                if raw_regime_value_from_context == MarketRegime.BEAR.value.upper():
                    final_confidence = max(0.0, final_confidence - bear_bear_confidence_boost)
                elif raw_regime_value_from_context == MarketRegime.BULL.value.upper():
                    final_confidence = 0.5 + (final_confidence - 0.5) * bull_bear_confidence_dampen_factor

            # Ensure the returned dictionary matches AgentBase.execute expectations
            return {
                "verdict": verdict_str, 
                "confidence": round(float(final_confidence), 4),
                "details": {
                    "value": round(float(latest_k - latest_d), 4), # K-D difference
                    "k": round(float(latest_k), 4),
                    "d": round(float(latest_d), 4),
                    "prev_k": round(float(prev_k), 4),
                    "prev_d": round(float(prev_d), 4),
                    "oversold_threshold_used": round(float(oversold_threshold), 2),
                    "overbought_threshold_used": round(float(overbought_threshold), 2),
                    "params": current_params,
                    "market_regime_detected": raw_regime_value_from_context,
                    "volatility_factor_used": float(volatility_factor) # Added for completeness
                }
                # "data" field can be added here if there's other structured data to return
            }
        except Exception as e:
            self.logger.error(f"[{self.name}] Unhandled error in _execute for {symbol}: {e}", exc_info=True)
            # Corrected _error_response call
            return self._error_response(
                error_message=f"Unhandled agent error in _execute: {str(e)}",
                details={
                    "exception_type": type(e).__name__, 
                    "exception_message": str(e),
                    "symbol": symbol,
                    "params": locals().get('current_params', 'not set')
                }
            )
