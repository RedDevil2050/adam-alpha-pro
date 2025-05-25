from backend.agents.base.category_bases import TechnicalAgent # Corrected import
from backend.models.common_models import VerdictType # Import VerdictType for string constants
from backend.config.settings import AgentSettings # For type hinting in run fn
from backend.data.providers.base_provider import BaseDataProvider # For type hinting in run fn

from datetime import datetime, timedelta
import pandas as pd
from loguru import logger # Keep for the run function if it uses it directly
import json
import numpy as np
from typing import Any, Dict # Added Dict for type hinting

from backend.agents.decorators import standard_agent_execution

AGENT_NAME = "stochastic_oscillator_agent" # Use constant convention


class StochasticOscillatorAgent(TechnicalAgent):
    # __init__ is inherited from TechnicalAgent, which calls AgentBase.__init__
    # AgentBase.__init__(self, name, settings, logger, cache_client, data_provider, market_context_provider)

    async def execute(self, symbol: str, agent_outputs: Dict = None, k_period: int = 14, d_period: int = 3, smoothing: int = 3) -> Dict:
        """
        Executes the agent's logic, including fetching data, calculating Stochastic Oscillator,
        and determining a verdict. Overrides AgentBase.execute to handle specific parameters.
        """
        agent_outputs = agent_outputs or {}
        # self.logger is initialized by AgentBase
        self.logger.debug(f"[{self.name}] Executing for {symbol} with k={k_period}, d={d_period}, s={smoothing}")

        # self.cache_client and self.settings are initialized by AgentBase
        if self.cache_client and self.settings.agent_cache_enabled:
            cache_key = self._generate_cache_key(symbol, agent_outputs, k_period=k_period, d_period=d_period, smoothing=smoothing)
            cached_result_str = await self.cache_client.get(cache_key)
            if cached_result_str:
                try:
                    cached_result = json.loads(cached_result_str)
                    self.logger.debug(f"[{self.name}] Cache hit for {symbol} with key {cache_key}")
                    return cached_result
                except json.JSONDecodeError:
                    self.logger.warning(f"[{self.name}] Failed to decode cached JSON for {cache_key}. Refetching.")
            else:
                self.logger.debug(f"[{self.name}] Cache miss for {symbol} with key {cache_key}")

        raw_result = await self._execute(symbol, agent_outputs, k_period=k_period, d_period=d_period, smoothing=smoothing)

        # _format_output is defined in AgentBase
        formatted_result = self._format_output(symbol, raw_result, agent_outputs)


        if self.cache_client and self.settings.agent_cache_enabled and \
           formatted_result.get("verdict") not in [VerdictType.NO_DATA.value, VerdictType.ERROR.value, None]:
            cache_key_for_set = self._generate_cache_key(symbol, agent_outputs, k_period=k_period, d_period=d_period, smoothing=smoothing)
            await self.cache_client.set(cache_key_for_set, json.dumps(formatted_result), ex=self.settings.agent_cache_ttl_seconds)
            self.logger.debug(f"[{self.name}] Cached result for {symbol} with key {cache_key_for_set}")

        return formatted_result

    async def _execute(self, symbol: str, agent_outputs: Dict, k_period: int = 14, d_period: int = 3, smoothing: int = 3) -> Dict:
        try:
            # Fetch market context using AgentBase's method
            market_context_data = await self.get_market_context(symbol)
            current_market_regime = market_context_data.get("regime", "UNKNOWN").upper() # Ensure "BULL", "BEAR" etc.
            volatility_factor = market_context_data.get("volatility_factor", 1.0)
            
            self.logger.debug(f"[{self.name}] Market context for {symbol}: Regime='{current_market_regime}', VolatilityFactor={volatility_factor}")

            current_params = {"k": k_period, "d": d_period, "s": smoothing}

            # Fetch data using self.data_provider (from AgentBase)
            end_date = datetime.now().date()
            required_data_points = (k_period - 1) + (smoothing - 1) + (d_period - 1) + 2
            start_date = end_date - timedelta(days=required_data_points + 60) # Buffer

            # self.data_provider is initialized by AgentBase
            if not self.data_provider:
                 self.logger.error(f"[{self.name}] Data provider not initialized.")
                 return self._error_response(symbol, "Data provider not available.", details={"params": current_params})

            df = await self.data_provider.fetch_ohlcv_series(symbol, start_date=start_date, end_date=end_date, interval='1d')

            if df is None or df.empty or len(df) < required_data_points:
                self.logger.warning(f"[{self.name}] Insufficient data for {symbol}. Need {required_data_points}, got {len(df) if df is not None else 0}.")
                return self._error_response(
                    symbol,
                    f"Insufficient OHLCV data (need {required_data_points}, got {len(df) if df is not None else 0})",
                    details={"params": current_params, "market_regime": current_market_regime}
                )

            if not all(col in df.columns for col in ['high', 'low', 'close']):
                self.logger.error(f"[{self.name}] Missing required OHLC columns in data for {symbol}.")
                return self._error_response(symbol, "Missing OHLC columns.", details={"params": current_params, "market_regime": current_market_regime})

            df_copy = df.copy()
            df_copy.loc[:, 'low_min'] = df_copy["low"].rolling(window=k_period, min_periods=k_period).min()
            df_copy.loc[:, 'high_max'] = df_copy["high"].rolling(window=k_period, min_periods=k_period).max()
            
            denominator = df_copy['high_max'] - df_copy['low_min']
            df_copy.loc[:, 'fast_k'] = 100 * ((df_copy["close"] - df_copy['low_min']) / denominator.replace(0, np.nan))
            df_copy.loc[:, 'fast_k'] = df_copy['fast_k'].fillna(50)

            df_copy.loc[:, 'k_series'] = df_copy['fast_k'].rolling(window=smoothing, min_periods=smoothing).mean()
            df_copy.loc[:, 'd_series'] = df_copy['k_series'].rolling(window=d_period, min_periods=d_period).mean()

            if df_copy['k_series'].iloc[-2:].isna().any() or df_copy['d_series'].iloc[-2:].isna().any():
                self.logger.warning(f"[{self.name}] NaN values in K or D series for {symbol} after rolling.")
                return self._error_response(
                    symbol,
                    "NaN values in K or D series after rolling, likely due to gaps in data.",
                    details={"params": current_params, "market_regime": current_market_regime}
                )

            latest_k, latest_d = float(df_copy['k_series'].iloc[-1]), float(df_copy['d_series'].iloc[-1])
            prev_k, prev_d = float(df_copy['k_series'].iloc[-2]), float(df_copy['d_series'].iloc[-2])

            # Access stochastic-specific settings from self.settings.stochastic_oscillator
            # Ensure StochasticOscillatorSettings is part of AgentSettings and passed correctly.
            # Using .get() for dictionary-like access, assuming self.settings.stochastic_oscillator is a dict or Pydantic model.
            stoch_settings = self.settings.stochastic_oscillator if hasattr(self.settings, 'stochastic_oscillator') else {}

            base_oversold = stoch_settings.get("oversold_threshold", 20)
            base_overbought = stoch_settings.get("overbought_threshold", 80)
            
            oversold_threshold = float(base_oversold)
            overbought_threshold = float(base_overbought)

            bull_adjustment = stoch_settings.get("bull_market_oversold_adjustment", 5)
            bear_adjustment = stoch_settings.get("bear_market_oversold_adjustment", -5) # e.g. -5 to lower threshold
            volatility_sensitivity = stoch_settings.get("volatility_threshold_sensitivity", 0.2)


            if current_market_regime == "BULL":
                oversold_threshold += bull_adjustment
            elif current_market_regime == "BEAR":
                oversold_threshold += bear_adjustment 
            
            if volatility_factor != 1.0:
                oversold_adjustment_factor = (volatility_factor - 1.0) * volatility_sensitivity
                overbought_adjustment_factor = (volatility_factor - 1.0) * volatility_sensitivity
                oversold_threshold = base_oversold * (1 - oversold_adjustment_factor)
                overbought_threshold = base_overbought * (1 + overbought_adjustment_factor)

            oversold_threshold = max(5.0, min(40.0, oversold_threshold))
            overbought_threshold = min(95.0, max(60.0, overbought_threshold))
            if oversold_threshold >= overbought_threshold: # Safety reset
                oversold_threshold = float(base_oversold)
                overbought_threshold = float(base_overbought)
            
            verdict_str = VerdictType.HOLD_NEUTRAL.value 
            base_signal_strength = 0.5

            if prev_k <= prev_d and latest_k > latest_d: # Bullish Crossover
                if latest_k < oversold_threshold + 10:
                    verdict_str = VerdictType.BUY_OVERSOLD_CROSS.value
                    base_signal_strength = 0.80
                    if latest_k < oversold_threshold:
                        base_signal_strength = min(1.0, base_signal_strength + 0.10)
                elif latest_k < 50:
                    verdict_str = VerdictType.BUY_CROSS_BELOW_50.value
                    base_signal_strength = 0.65
                else:
                    verdict_str = VerdictType.HOLD_BULLISH_CROSS_UPPER.value
                    base_signal_strength = 0.55
            elif prev_k >= prev_d and latest_k < latest_d: # Bearish Crossover
                if latest_k > overbought_threshold - 10:
                    verdict_str = VerdictType.SELL_OVERBOUGHT_CROSS.value
                    base_signal_strength = 0.20
                    if latest_k > overbought_threshold:
                        base_signal_strength = max(0.0, base_signal_strength - 0.10)
                elif latest_k > 50:
                    verdict_str = VerdictType.SELL_CROSS_ABOVE_50.value
                    base_signal_strength = 0.35
                else:
                    verdict_str = VerdictType.HOLD_BEARISH_CROSS_LOWER.value
                    base_signal_strength = 0.45
            
            final_confidence = base_signal_strength
            
            bull_bull_confidence_boost = stoch_settings.get("bull_market_bullish_signal_boost", 0.1)
            bull_bear_confidence_dampen_factor = stoch_settings.get("bull_market_bearish_signal_dampen_factor", 0.15) 
            bear_bear_confidence_boost = stoch_settings.get("bear_market_bearish_signal_boost", -0.1) 
            bear_bull_confidence_dampen_factor = stoch_settings.get("bear_market_bullish_signal_dampen_factor", 0.85)


            if final_confidence > 0.5: # Bullish signal
                if current_market_regime == "BULL":
                    final_confidence = min(1.0, final_confidence + bull_bull_confidence_boost)
                elif current_market_regime == "BEAR":
                    final_confidence = final_confidence * bear_bull_confidence_dampen_factor
            elif final_confidence < 0.5: # Bearish signal
                if current_market_regime == "BEAR":
                    final_confidence = max(0.0, final_confidence + bear_bear_confidence_boost) 
                elif current_market_regime == "BULL":
                    final_confidence = final_confidence + (0.5 - final_confidence) * bull_bear_confidence_dampen_factor

            return {
                # "symbol": symbol, # Added by _format_output
                "verdict": verdict_str, 
                "confidence": round(final_confidence, 4),
                "value": round(latest_k - latest_d, 4),
                "details": {
                    "k": round(latest_k, 4),
                    "d": round(latest_d, 4),
                    "prev_k": round(prev_k, 4),
                    "prev_d": round(prev_d, 4),
                    "oversold_threshold_used": round(oversold_threshold, 2),
                    "overbought_threshold_used": round(overbought_threshold, 2),
                    "params": current_params,
                    "market_regime_detected": current_market_regime,
                    "volatility_factor_used": volatility_factor
                },
                "score": round(base_signal_strength, 4), # Raw score before regime adjustment
                # "agent_name": self.name, # Added by _format_output
            }
        except Exception as e:
            self.logger.error(f"Error in {self.name} for {symbol}: {e}", exc_info=True)
            cmr_for_error = "UNKNOWN"
            if 'current_market_regime' in locals():
                cmr_for_error = current_market_regime
            elif 'market_context_data' in locals() and market_context_data:
                 cmr_for_error = market_context_data.get("regime", "UNKNOWN").upper()

            return self._error_response(
                symbol, 
                str(e), 
                details={
                    "params": {"k": k_period, "d": d_period, "s": smoothing} if 'k_period' in locals() else {}, 
                    "market_regime_at_error": cmr_for_error
                }
            )

    # _generate_cache_key is inherited from AgentBase if not overridden.
    # The agent's current _generate_cache_key is specific to its params, so keep it.
    def _generate_cache_key(self, symbol: str, agent_outputs: Dict, **kwargs) -> str:
        # Ensure kwargs (like k_period, d_period) are sorted for consistent key generation
        param_string = ":".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
        # Include agent_outputs in cache key if its content can vary and affect results.
        # For now, assuming agent_outputs is not used by this agent's core logic beyond being passed around.
        # If it were, a more robust hashing of agent_outputs might be needed.
        return f"{self.name}:{symbol}:{param_string}"

    # _format_output is inherited from AgentBase.
    # The default implementation in AgentBase should be sufficient if _execute returns a dict
    # with fields like 'verdict', 'confidence', 'details', 'value', 'score'.
    # AgentBase._format_output adds 'agent_name', 'symbol', 'timestamp'.


@standard_agent_execution(agent_name=AGENT_NAME, category="technical")
async def run(
    # Standard arguments provided by the execution framework/decorator
    symbol: str,
    agent_outputs: Dict, # Dict of outputs from previous agents in a chain/workflow
    settings: AgentSettings, 
    data_provider: BaseDataProvider,
    cache_client: Any, # Typically a Redis client instance
    logger_instance: Any, # Logger instance (e.g., loguru logger)
    market_context_provider: Any, # Provider for market context data
    # Agent-specific parameters, these will be passed through from the orchestrator/API call
    k_period: int = 14,
    d_period: int = 3,
    smoothing: int = 3
) -> Dict:
    """
    Entry point for the Stochastic Oscillator Agent.
    Instantiates the agent and runs its execution logic.
    """
    # The 'settings' object passed here is the global AgentSettings.
    # The agent's __init__ (via AgentBase) will typically expect its specific settings,
    # often found under a key like settings.agent_specific_settings.stochastic_oscillator or similar.
    # For AgentBase, it expects the relevant settings slice for *this* agent.
    # Assuming AgentBase or TechnicalAgent handles extracting its relevant settings portion
    # or that 'settings.stochastic_oscillator' is directly what the agent needs.
    # If AgentBase expects the *entire* AgentSettings object and internally looks up its name, that's also possible.
    # Let's assume AgentBase constructor is: __init__(self, name, settings_for_this_agent, logger, ...)
    # The standard_agent_execution decorator might prepare/pass the correct slice of settings.
    # For now, we pass the whole 'settings' object, and AgentBase/StochasticOscillatorAgent
    # will access `settings.stochastic_oscillator` or `settings.agent_settings[AGENT_NAME]` as needed.
    # The current StochasticOscillatorAgent accesses self.settings.stochastic_oscillator.

    agent = StochasticOscillatorAgent(
        name=AGENT_NAME,
        settings=settings, # Pass the main settings object
        logger=logger_instance,
        cache_client=cache_client,
        data_provider=data_provider,
        market_context_provider=market_context_provider
    )
    return await agent.execute(
        symbol=symbol, 
        agent_outputs=agent_outputs, 
        k_period=k_period, 
        d_period=d_period, 
        smoothing=smoothing
    )
