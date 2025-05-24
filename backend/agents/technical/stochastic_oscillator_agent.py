from backend.agents.technical.base import TechnicalAgent
from backend.utils.data_provider import fetch_ohlcv_series
# from backend.utils.cache_utils import get_redis_client # Not directly needed if using self.cache
from backend.agents.technical.utils import tracker
from datetime import datetime, timedelta # Added imports
import pandas as pd
from loguru import logger
import json # Added for caching
import numpy as np # For NaN checks and potential calculations

# agent_name should be defined by the class instance (self.name) or passed to decorator
agent_name = "stochastic_oscillator_agent"


class StochasticOscillatorAgent(TechnicalAgent):
    async def execute(self, symbol: str, agent_outputs: dict = None, k_period: int = 14, d_period: int = 3, smoothing: int = 3) -> dict:
        """
        Executes the agent's logic, including fetching data, calculating Stochastic Oscillator,
        and determining a verdict. Overrides AgentBase.execute to handle specific parameters.
        """
        # Assuming self.initialize() is called by AgentBase constructor or a similar mechanism
        # to set up self.cache_client, self.settings, self.logger etc.
        # If not, it would need to be called: await self.initialize()

        agent_outputs = agent_outputs or {}
        self.logger.debug(f"[{self.name}] Executing for {symbol} with k={k_period}, d={d_period}, s={smoothing}")

        # Check cache first
        if self.cache_client: # Use self.cache_client (assuming renamed for clarity)
            # Pass extra args to _generate_cache_key through kwargs
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

        formatted_result = self._format_output(symbol, raw_result)

        if self.cache_client and formatted_result.get("verdict") not in ["NO_DATA", "ERROR", None]:
            # Regeneration of cache_key here is redundant if done above, but ensure consistency if logic changes
            cache_key_for_set = self._generate_cache_key(symbol, agent_outputs, k_period=k_period, d_period=d_period, smoothing=smoothing)
            await self.cache_client.set(cache_key_for_set, json.dumps(formatted_result), ex=self.settings.agent_cache_ttl_seconds)
            self.logger.debug(f"[{self.name}] Cached result for {symbol} with key {cache_key_for_set}")

        return formatted_result

    async def _execute(self, symbol: str, agent_outputs: dict, k_period: int = 14, d_period: int = 3, smoothing: int = 3) -> dict:
        try:
            # Cache key generation
            cache_key = f"{agent_name}:{symbol}:{k_period}:{d_period}:{smoothing}"
            # redis_client = await get_redis_client() # This is already part of self.cache from TechnicalAgent.initialize()
            # Cache check - Handled by the public execute method using self.cache_client and self._generate_cache_key

            # Fetch market context
            market_context = None
            current_market_regime = "UNKNOWN"
            volatility_factor = 1.0 # Default
            # Assuming market_context_provider is injected
            if hasattr(self, 'market_context_provider') and self.market_context_provider:
                try:
                    market_context = await self.market_context_provider.get_context(symbol) # Example method
                    if market_context and "regime" in market_context:
                        current_market_regime = market_context["regime"]
                    if market_context and "volatility_factor" in market_context: # e.g. from ATR normalized
                        volatility_factor = market_context["volatility_factor"]
                except Exception as mc_e:
                    self.logger.warning(f"[{self.name}] Failed to get market context for {symbol}: {mc_e}")

            current_params = {"k": k_period, "d": d_period, "s": smoothing}

            # Fetch data
            end_date = datetime.now().date()
            # Calculate required data points for Stoch Osc with smoothing and prev values
            # k_period for initial rolling, smoothing for %K, d_period for %D, +1 for prev values access (iloc[-2])
            required_data_points = (k_period -1) + (smoothing -1) + (d_period -1) + 2 
            # Fetch a bit more buffer
            start_date = end_date - timedelta(days=required_data_points + 60) # Increased buffer for data fetching
            # Assuming self.data_provider is injected
            df = await self.data_provider.fetch_ohlcv_series(symbol, start_date=start_date, end_date=end_date, interval='1d')

            if df is None or df.empty or len(df) < required_data_points:
                self.logger.warning(f"[{self.name}] Insufficient data for {symbol}. Need {required_data_points}, got {len(df) if df is not None else 0}.")
                # Use self._error_response for consistency if it's well-defined in base
                return {
                    "symbol": symbol,
                    "verdict": "NO_DATA",
                    "confidence": 0.0,
                    "value": None,
                    "details": {
                        "reason": f"Insufficient OHLCV data (need {required_data_points}, got {len(df) if df is not None else 0})",
                        "params": current_params,
                        "market_regime": current_market_regime
                    },
                    "agent_name": self.name,
                }

            # Compute Stochastic Oscillator
            # Ensure 'high', 'low', 'close' columns exist
            if not all(col in df.columns for col in ['high', 'low', 'close']):
                self.logger.error(f"[{self.name}] Missing required OHLC columns in data for {symbol}.")
                return self._error_response(symbol, "Missing OHLC columns.") # Assuming _error_response exists

            # Avoid division by zero if high_max == low_min
            df_copy = df.copy() # Work on a copy to avoid SettingWithCopyWarning
            df_copy.loc[:, 'low_min'] = df_copy["low"].rolling(window=k_period, min_periods=k_period).min()
            df_copy.loc[:, 'high_max'] = df_copy["high"].rolling(window=k_period, min_periods=k_period).max()
            
            # Handle cases where high_max might be equal to low_min (e.g., flat price action)
            denominator = df_copy['high_max'] - df_copy['low_min']
            df_copy.loc[:, 'fast_k'] = 100 * ((df_copy["close"] - df_copy['low_min']) / denominator.replace(0, np.nan))
            df_copy['fast_k'].fillna(50, inplace=True) # If denominator was 0, K is often set to 50

            # Slow %K (smoothed Fast %K using the 'smoothing' parameter)
            df_copy.loc[:, 'k_series'] = df_copy['fast_k'].rolling(window=smoothing, min_periods=smoothing).mean()
            # Slow %D (SMA of Slow %K)
            df_copy.loc[:, 'd_series'] = df_copy['k_series'].rolling(window=d_period, min_periods=d_period).mean()

            # Check for NaNs after rolling operations
            if df_copy['k_series'].iloc[-2:].isna().any() or df_copy['d_series'].iloc[-2:].isna().any():
                self.logger.warning(f"[{self.name}] NaN values in K or D series for {symbol} after rolling. Insufficient consecutive data.")
                return { # Or use self._error_response
                    "symbol": symbol,
                    "verdict": "NO_DATA",
                    "confidence": 0.0,
                    "value": None,
                    "details": {
                        "reason": "NaN values in K or D series after rolling, likely due to gaps in data.",
                        "params": current_params,
                        "market_regime": current_market_regime
                    },
                    "agent_name": self.name,
                }

            latest_k, latest_d = float(df_copy['k_series'].iloc[-1]), float(df_copy['d_series'].iloc[-1])
            prev_k, prev_d = float(df_copy['k_series'].iloc[-2]), float(df_copy['d_series'].iloc[-2])

            # --- Advanced Logic Integration ---
            # 1. Adaptive Thresholds
            base_oversold = 20
            base_overbought = 80
            oversold_threshold = float(base_oversold) # Ensure float for calculations
            overbought_threshold = float(base_overbought) # Ensure float for calculations

            if current_market_regime == "BULL":
                oversold_threshold += 5 
                # overbought_threshold += 0 # No change or slightly higher if preferred
            elif current_market_regime == "BEAR":
                oversold_threshold -= 5
                # overbought_threshold -= 0 # No change or slightly lower if preferred
            
            # Adjust for volatility_factor (e.g., volatility_factor > 1 means higher volatility)
            # Higher volatility might widen the bands slightly.
            # Factor of 0.1 means 10% of (volatility_factor - 1) effect.
            # Example: if vol_factor is 1.2 (20% higher vol), oversold decreases by 20%*0.1*base_oversold = 0.02*base_oversold
            #          overbought increases by 0.02*base_overbought
            if volatility_factor != 1.0:
                oversold_adjustment = (volatility_factor - 1.0) * 0.2 # More sensitive adjustment: 20% of volatility deviation
                overbought_adjustment = (volatility_factor - 1.0) * 0.2

                oversold_threshold = base_oversold * (1 - oversold_adjustment)
                overbought_threshold = base_overbought * (1 + overbought_adjustment)

            # Ensure thresholds are within reasonable bounds
            oversold_threshold = max(5.0, min(40.0, oversold_threshold))
            overbought_threshold = min(95.0, max(60.0, overbought_threshold))
            if oversold_threshold >= overbought_threshold: # Safety check
                oversold_threshold = float(base_oversold)
                overbought_threshold = float(base_overbought)


            verdict = "HOLD_NEUTRAL"
            # base_signal_strength: 0.0 (strong sell) to 0.5 (neutral) to 1.0 (strong buy)
            base_signal_strength = 0.5 

            # 2. Enhanced Crossover Logic & Base Signal Strength
            # Bullish Crossover: %K crosses above %D
            if prev_k <= prev_d and latest_k > latest_d:
                if latest_k < oversold_threshold + 10: # Crossover in/near oversold
                    verdict = "BUY_OVERSOLD_CROSS"
                    base_signal_strength = 0.80
                    if latest_k < oversold_threshold: # Deep in oversold
                        base_signal_strength = min(1.0, base_signal_strength + 0.10)
                elif latest_k < 50 : # Crossover below midline
                    verdict = "BUY_CROSS_BELOW_50"
                    base_signal_strength = 0.65
                else: # Crossover above midline
                    verdict = "HOLD_BULLISH_CROSS_UPPER"
                    base_signal_strength = 0.55

            # Bearish Crossover: %K crosses below %D
            elif prev_k >= prev_d and latest_k < latest_d:
                if latest_k > overbought_threshold - 10: # Crossover in/near overbought
                    verdict = "SELL_OVERBOUGHT_CROSS"
                    base_signal_strength = 0.20
                    if latest_k > overbought_threshold: # Deep in overbought
                        base_signal_strength = max(0.0, base_signal_strength - 0.10)
                elif latest_k > 50: # Crossover above midline
                    verdict = "SELL_CROSS_ABOVE_50"
                    base_signal_strength = 0.35
                else: # Crossover below midline
                    verdict = "HOLD_BEARISH_CROSS_LOWER"
                    base_signal_strength = 0.45
            
            # 3. Calibrated Confidence Score
            final_confidence = base_signal_strength

            # Adjust confidence based on market regime
            if final_confidence > 0.5: # Bullish signal
                if current_market_regime == "BULL":
                    final_confidence = min(1.0, final_confidence + 0.1)
                elif current_market_regime == "BEAR":
                    final_confidence = final_confidence * 0.85 # Dampen bullish signal in bear market
            elif final_confidence < 0.5: # Bearish signal
                if current_market_regime == "BEAR":
                    final_confidence = max(0.0, final_confidence - 0.1)
                elif current_market_regime == "BULL":
                    # Dampen bearish signal in bull market (move towards 0.5, making it weaker sell)
                    final_confidence = final_confidence + (0.5 - final_confidence) * 0.15 


            # (Optional) Further adjustment by volatility for confidence can be added here if desired
            # For example, very high volatility might slightly reduce certainty for non-extreme signals.

            result = {
                "symbol": symbol,
                "verdict": verdict,
                "confidence": round(final_confidence, 4),
                "value": round(latest_k - latest_d, 4), # Difference between K and D
                "details": {
                    "k": round(latest_k, 4),
                    "d": round(latest_d, 4),
                    "prev_k": round(prev_k, 4),
                    "prev_d": round(prev_d, 4),
                    "oversold_threshold": round(oversold_threshold, 2),
                    "overbought_threshold": round(overbought_threshold, 2),
                    "params": current_params,
                    "market_regime": current_market_regime,
                    "volatility_factor_used": volatility_factor 
                },
                "score": round(base_signal_strength, 4), # Store pre-calibration score
                "agent_name": self.name,
            }

            # Caching is handled by the execute() method which calls _format_output and then caches that.
            # No direct caching here in _execute to avoid caching raw_result.
            # tracker.update("technical", agent_name, "implemented") # Tracker update should be in execute or decorator
            return result
        except Exception as e:
            self.logger.error(f"Error in {self.name} for {symbol}: {e}", exc_info=True)
            # Use self._error_response for consistency
            return { # Or self._error_response(symbol, str(e), details=...)
                "symbol": symbol,
                "verdict": "ERROR",
                "confidence": 0.0,
                "value": None,
                "details": {
                    "error": str(e),
                    "params": {"k": k_period, "d": d_period, "s": smoothing}, # Ensure params are here
                    "market_regime": current_market_regime if 'current_market_regime' in locals() else "UNKNOWN"
                },
                "agent_name": self.name,
            }

    # Placeholder for _format_output if not in base
    def _format_output(self, symbol: str, raw_result: dict) -> dict:
        # This method would ensure the output structure is consistent
        # For now, assume raw_result is already in the desired format
        return raw_result

    # Placeholder for _generate_cache_key if not in base
    def _generate_cache_key(self, symbol: str, agent_outputs: dict, **kwargs) -> str:
        # Ensure kwargs (like k_period, d_period) are sorted for consistent key generation
        param_string = ":".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
        return f"{self.name}:{symbol}:{param_string}"


async def run(symbol: str, agent_outputs: dict = {}, k_period: int = 14, d_period: int = 3, smoothing: int = 3) -> dict:
    # In a real scenario, dependencies like data_provider, cache_client, settings
    # would be instantiated and passed to the agent's constructor.
    # For simplicity here, we assume they are handled by the agent's __init__ or initialize methods.
    # This standalone 'run' function might be better suited for decoration by standard_agent_execution
    # if the class instantiation and dependency injection is handled within the decorator or a factory.

    # Example:
    # settings = get_settings_instance()
    # cache_client = await get_cache_client_instance()
    # data_provider = get_data_provider_instance()
    # market_context_provider = get_market_context_provider_instance()
    # agent = StochasticOscillatorAgent(name=agent_name, settings=settings.agent_settings.stochastic_oscillator, 
    #                                   logger=logger, cache_client=cache_client, 
    #                                   data_provider=data_provider, market_context_provider=market_context_provider)

    agent = StochasticOscillatorAgent(name=agent_name, logger=logger) # Simplified instantiation
    # Pass the parameters to the overridden execute method
    return await agent.execute(symbol, agent_outputs, k_period=k_period, d_period=d_period, smoothing=smoothing)
