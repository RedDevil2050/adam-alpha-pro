from backend.agents.base.category_bases import TechnicalAgentBase # Corrected import
from backend.models.common_models import VerdictType, MarketRegime # Import MarketRegime
from backend.config.settings import AgentSettings # For type hinting in run fn
from backend.data.providers.base_provider import BaseDataProvider # For type hinting in run fn

from datetime import datetime, timedelta
from loguru import logger # Keep for the run function if it uses it directly
from typing import Any, Dict # Added Dict for type hinting
import json # Added for JSONDecodeError
import numpy as np # Added for np.nan

from backend.agents.decorators import standard_agent_execution

AGENT_NAME = "stochastic_oscillator_agent" # Use constant convention


class StochasticOscillatorAgent(TechnicalAgentBase):
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
                    return cached_result # Return the cached result
                except json.JSONDecodeError:
                    self.logger.warning(f"[{self.name}] Failed to decode cached JSON for {symbol}. Key: {cache_key}")
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
            
            # Revised regime handling:
            raw_regime_value_from_context = str(market_context_data.get("regime", MarketRegime.UNKNOWN.value)).upper()
            # raw_regime_value_from_context will be like "BULLISH", "BEARISH", etc.

            volatility_factor = market_context_data.get("volatility_factor", 1.0)
            
            self.logger.debug(f"[{self.name}] Market context for {symbol}: RegimeValue='{raw_regime_value_from_context}', VolatilityFactor={volatility_factor}")

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
                    details={"params": current_params, "market_regime": raw_regime_value_from_context} # Use the processed string value
                )

            if not all(col in df.columns for col in ['high', 'low', 'close']):
                self.logger.error(f"[{self.name}] Missing required OHLC columns in data for {symbol}.")
                return self._error_response(symbol, "Missing required OHLC columns.", details={"params": current_params, "market_regime": raw_regime_value_from_context})


            df_copy = df.copy()
            df_copy.loc[:, 'low_min'] = df_copy["low"].rolling(window=k_period, min_periods=k_period).min()
            df_copy.loc[:, 'high_max'] = df_copy["high"].rolling(window=k_period, min_periods=k_period).max()
            
            denominator = df_copy['high_max'] - df_copy['low_min']
            df_copy.loc[:, 'fast_k'] = 100 * ((df_copy["close"] - df_copy['low_min']) / denominator.replace(0, np.nan)) # Use np.nan
            df_copy.loc[:, 'fast_k'] = df_copy['fast_k'].fillna(50)

            df_copy.loc[:, 'k_series'] = df_copy['fast_k'].rolling(window=smoothing, min_periods=smoothing).mean()
            df_copy.loc[:, 'd_series'] = df_copy['k_series'].rolling(window=d_period, min_periods=d_period).mean()

            if df_copy['k_series'].iloc[-2:].isna().any() or df_copy['d_series'].iloc[-2:].isna().any():
                self.logger.warning(f"[{self.name}] NaN values in k_series or d_series for {symbol} before selecting latest/prev.")
                return self._error_response(symbol, "NaN in K or D series.", details={"params": current_params, "market_regime": raw_regime_value_from_context})
                pass # Placeholder

            latest_k, latest_d = df_copy['k_series'].iloc[-1], df_copy['d_series'].iloc[-1] # Assuming this was intended
            prev_k, prev_d = df_copy['k_series'].iloc[-2], df_copy['d_series'].iloc[-2] # Assuming this was intended

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
            volatility_sensitivity = stoch_settings.get("volatility_threshold_sensitivity", 0.2) # Not used yet


            # Compare with uppercased enum *values*
            if raw_regime_value_from_context == MarketRegime.BULL.value.upper(): # e.g., "BULLISH"
                oversold_threshold += bull_adjustment
            elif raw_regime_value_from_context == MarketRegime.BEAR.value.upper(): # e.g., "BEARISH"
                 oversold_threshold += bear_adjustment
            
            if volatility_factor != 1.0:
                # Example: Adjust thresholds based on volatility
                threshold_range_adjustment = (overbought_threshold - oversold_threshold) * (volatility_factor - 1.0) * volatility_sensitivity
                oversold_threshold -= threshold_range_adjustment / 2
                overbought_threshold += threshold_range_adjustment / 2
            
            oversold_threshold = max(5.0, min(40.0, oversold_threshold)) # Clamp after adjustments
            overbought_threshold = min(95.0, max(60.0, overbought_threshold)) # Clamp after adjustments
            if oversold_threshold >= overbought_threshold:                
                self.logger.warning(f"[{self.name}] Oversold threshold ({oversold_threshold}) >= overbought threshold ({overbought_threshold}) for {symbol}. Clamping.")
                oversold_threshold = min(oversold_threshold, overbought_threshold - 1) # Ensure separation
            
            verdict_str = VerdictType.HOLD_NEUTRAL.value 
            base_signal_strength = 0.5 # Neutral confidence

            # Crossover logic
            if prev_k <= prev_d and latest_k > latest_d: # Bullish crossover (%K crosses above %D)
                if latest_k < oversold_threshold + 10 : # Crossover from oversold or near oversold
                    verdict_str = VerdictType.BUY_OVERSOLD_CROSS.value
                    base_signal_strength = 0.75 # Higher confidence for oversold buy
                else: # General bullish crossover
                    verdict_str = VerdictType.BUY.value 
                    base_signal_strength = 0.65
            elif prev_k >= prev_d and latest_k < latest_d: # Bearish crossover (%K crosses below %D)
                if latest_k > overbought_threshold - 10: # Crossover from overbought or near overbought
                    verdict_str = VerdictType.SELL_OVERBOUGHT_CROSS.value
                    base_signal_strength = 0.25 # Lower confidence for overbought sell (0 to 1 scale, 0.5 is neutral)
                else: # General bearish crossover
                    verdict_str = VerdictType.SELL.value
                    base_signal_strength = 0.35
            
            final_confidence = base_signal_strength
            
            # Regime-based confidence adjustment
            bull_bull_confidence_boost = stoch_settings.get("bull_market_bullish_signal_boost", 0.1) # Additive
            bull_bear_confidence_dampen_factor = stoch_settings.get("bull_market_bearish_signal_dampen_factor", 0.8) # Multiplicative
            bear_bear_confidence_boost = stoch_settings.get("bear_market_bearish_signal_boost", 0.1) # Additive to sell strength (i.e., makes it closer to 0 or 1)
            bear_bull_confidence_dampen_factor = stoch_settings.get("bear_market_bullish_signal_dampen_factor", 0.8) # Multiplicative

            if verdict_str in [VerdictType.BUY.value, VerdictType.BUY_OVERSOLD_CROSS.value]: # Bullish signal
                if raw_regime_value_from_context == MarketRegime.BULL.value.upper():
                    final_confidence = min(1.0, final_confidence + bull_bull_confidence_boost)
                elif raw_regime_value_from_context == MarketRegime.BEAR.value.upper():
                    final_confidence *= bear_bull_confidence_dampen_factor 
            elif verdict_str in [VerdictType.SELL.value, VerdictType.SELL_OVERBOUGHT_CROSS.value]: # Bearish signal
                # For bearish signals, confidence is typically 1 - strength.
                # Or, if base_signal_strength is already < 0.5 for sell, adjust it towards 0.
                if raw_regime_value_from_context == MarketRegime.BEAR.value.upper():
                    final_confidence = max(0.0, final_confidence - bear_bear_confidence_boost) # Making it a stronger sell (closer to 0)
                elif raw_regime_value_from_context == MarketRegime.BULL.value.upper():
                    final_confidence *= (1 + (1-bull_bear_confidence_dampen_factor)) # Dampen sell in bull market (closer to 0.5)


            return {
                "verdict": verdict_str, 
                "confidence": round(final_confidence, 4),
                "value": round(latest_k - latest_d, 4), # K-D difference
                "details": {
                    "k": round(latest_k, 4),
                    "d": round(latest_d, 4),
                    "prev_k": round(prev_k, 4),
                    "prev_d": round(prev_d, 4),
                    "oversold_threshold_used": round(oversold_threshold, 2),
                    "overbought_threshold_used": round(overbought_threshold, 2),
                    "params": current_params,
                    "market_regime_detected": raw_regime_value_from_context,
                    "volatility_factor_used": volatility_factor
                },
                "score": round(base_signal_strength, 4), # Raw signal strength before regime adjustment
            }
        except Exception as e:
            self.logger.error(f"Error in {self.name} for {symbol}: {e}", exc_info=True)
            cmr_for_error = MarketRegime.UNKNOWN.value.upper() 
            if 'raw_regime_value_from_context' in locals() and raw_regime_value_from_context:
                cmr_for_error = raw_regime_value_from_context
            elif 'market_context_data' in locals() and market_context_data:
                 cmr_for_error = str(market_context_data.get("regime", MarketRegime.UNKNOWN.value)).upper()

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
