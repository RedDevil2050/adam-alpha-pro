from backend.agents.technical.base import TechnicalAgent
from backend.utils.data_provider import fetch_ohlcv_series
from backend.utils.cache_utils import get_redis_client
from backend.agents.technical.utils import tracker
from datetime import datetime, timedelta # Added imports
import pandas as pd
from loguru import logger
import json # Added for caching

agent_name = "stochastic_oscillator_agent"


class StochasticOscillatorAgent(TechnicalAgent):
    async def execute(self, symbol: str, agent_outputs: dict = None, k_period: int = 14, d_period: int = 3, smoothing: int = 3) -> dict:
        """
        Executes the agent's logic, including fetching data, calculating Stochastic Oscillator,
        and determining a verdict. Overrides AgentBase.execute to handle specific parameters.
        """
        await self.initialize() # This should set self.cache from AgentBase
        agent_outputs = agent_outputs or {}

        # Check cache first
        if self.cache: # Use self.cache instead of self.redis_client
            # Pass extra args to _generate_cache_key through kwargs
            cache_key = self._generate_cache_key(symbol, agent_outputs, k_period=k_period, d_period=d_period, smoothing=smoothing)
            cached_result = await self.cache.get(cache_key) # Use self.cache
            if cached_result:
                logger.debug(f"[{self.name}] Cache hit for {symbol} with key {cache_key}")
                return json.loads(cached_result)
            logger.debug(f"[{self.name}] Cache miss for {symbol} with key {cache_key}")

        raw_result = await self._execute(symbol, agent_outputs, k_period=k_period, d_period=d_period, smoothing=smoothing)
        
        formatted_result = self._format_output(symbol, raw_result)
        
        if self.cache and formatted_result.get("verdict") not in ["NO_DATA", "ERROR", None]: # Use self.cache
            # Regeneration of cache_key here is redundant if done above, but ensure consistency if logic changes
            cache_key_for_set = self._generate_cache_key(symbol, agent_outputs, k_period=k_period, d_period=d_period, smoothing=smoothing)
            await self.cache.set(cache_key_for_set, json.dumps(formatted_result), ex=self.settings.agent_cache_ttl_seconds) # Use self.cache
            logger.debug(f"[{self.name}] Cached result for {symbol} with key {cache_key_for_set}")
            
        return formatted_result

    async def _execute(self, symbol: str, agent_outputs: dict, k_period: int = 14, d_period: int = 3, smoothing: int = 3) -> dict:
        try:
            # Cache key generation
            cache_key = f"{agent_name}:{symbol}:{k_period}:{d_period}:{smoothing}"
            # redis_client = await get_redis_client() # This is already part of self.cache from TechnicalAgent.initialize()
            # Cache check - Handled by the execute method using self.cache and self._generate_cache_key

            # Fetch market context
            market_context = None
            current_market_regime = "UNKNOWN"
            if hasattr(self, 'get_market_context') and callable(self.get_market_context):
                try:
                    market_context = await self.get_market_context(symbol)
                    if market_context and "regime" in market_context:
                        current_market_regime = market_context["regime"]
                except Exception as mc_e:
                    logger.warning(f"[{self.name}] Failed to get market context for {symbol}: {mc_e}")
            
            current_params = {"k": k_period, "d": d_period, "s": smoothing}

            # Fetch data
            end_date = datetime.now().date()
            # Calculate required data points for Stoch Osc with smoothing and prev values
            # k_period for initial rolling, smoothing for %K, d_period for %D, +1 for prev values access (iloc[-2])
            required_data_points = (k_period -1) + (smoothing -1) + (d_period -1) + 2 
            # Fetch a bit more buffer
            start_date = end_date - timedelta(days=required_data_points + 60) # Increased buffer for data fetching

            df = await fetch_ohlcv_series(symbol, start_date=start_date, end_date=end_date)

            if df is None or df.empty or len(df) < required_data_points:
                logger.warning(f"[{agent_name}] Insufficient data for {symbol}. Need {required_data_points}, got {len(df) if df is not None else 0}.")
                result = {
                    "symbol": symbol,
                    "verdict": "NO_DATA",
                    "confidence": 0.0,
                    "value": None,
                    "details": {
                        "reason": f"Insufficient OHLCV data (need {required_data_points}, got {len(df) if df is not None else 0})",
                        "params": current_params,
                        "market_regime": current_market_regime
                    },
                    "agent_name": agent_name,
                }
            else:
                # Compute Stochastic Oscillator
                low_min = df["low"].rolling(window=k_period, min_periods=k_period).min()
                high_max = df["high"].rolling(window=k_period, min_periods=k_period).max()
                
                fast_k = 100 * ((df["close"] - low_min) / (high_max - low_min))
                
                # Slow %K (smoothed Fast %K using the 'smoothing' parameter)
                k_series = fast_k.rolling(window=smoothing, min_periods=smoothing).mean()
                
                # Slow %D (SMA of Slow %K)
                d_series = k_series.rolling(window=d_period, min_periods=d_period).mean()

                # Check for NaNs after rolling operations, which can happen if min_periods are not met despite overall length
                if k_series.iloc[-2:].isna().any() or d_series.iloc[-2:].isna().any():
                    logger.warning(f"[{agent_name}] NaN values in K or D series for {symbol} after rolling. Insufficient consecutive data.")
                    return {
                        "symbol": symbol,
                        "verdict": "NO_DATA",
                        "confidence": 0.0,
                        "value": None,
                        "details": {
                            "reason": "NaN values in K or D series after rolling, likely due to gaps in data.",
                            "params": current_params,
                            "market_regime": current_market_regime
                        },
                        "agent_name": agent_name,
                    }

                latest_k, latest_d = float(k_series.iloc[-1]), float(d_series.iloc[-1])
                prev_k, prev_d = float(k_series.iloc[-2]), float(d_series.iloc[-2])

                OVERSOLD_THRESHOLD = 20
                OVERBOUGHT_THRESHOLD = 80

                verdict = "HOLD"
                score = 0.5

                # Crossover logic (using Slow %K and Slow %D)
                # Buy signal: %K crosses above %D in the oversold region.
                if prev_k <= prev_d and latest_k > latest_d and latest_k < OVERSOLD_THRESHOLD and prev_k < OVERSOLD_THRESHOLD:
                    verdict = "BUY"
                    score = 1.0 
                # Sell/Avoid signal: %K crosses below %D in the overbought region.
                elif prev_k >= prev_d and latest_k < latest_d and latest_k > OVERBOUGHT_THRESHOLD and prev_k > OVERBOUGHT_THRESHOLD:
                    verdict = "AVOID"
                    score = 0.0
                
                result = {
                    "symbol": symbol,
                    "verdict": verdict,
                    "confidence": score,
                    "value": round(latest_k - latest_d, 4), # Difference between K and D
                    "details": {
                        "k": round(latest_k, 4), 
                        "d": round(latest_d, 4),
                        "params": current_params,
                        "market_regime": current_market_regime
                    },
                    "score": score,
                    "agent_name": agent_name,
                }

            # Caching is handled by the execute() method which calls _format_output and then caches that.
            # No direct caching here in _execute to avoid caching raw_result.
            # tracker.update("technical", agent_name, "implemented") # Tracker update should be in execute or decorator
            return result
        except Exception as e:
            logger.error(f"Error in {agent_name} for {symbol}: {e}", exc_info=True)
            return {
                "symbol": symbol,
                "verdict": "ERROR",
                "confidence": 0.0,
                "value": None,
                "details": {
                    "error": str(e),
                    "params": {"k": k_period, "d": d_period, "s": smoothing}, # Ensure params are here
                    "market_regime": "UNKNOWN" # And market_regime
                    },
                "agent_name": agent_name,
            }


async def run(symbol: str, agent_outputs: dict = {}, k_period: int = 14, d_period: int = 3, smoothing: int = 3) -> dict:
    agent = StochasticOscillatorAgent()
    # Pass the parameters to the overridden execute method
    return await agent.execute(symbol, agent_outputs, k_period=k_period, d_period=d_period, smoothing=smoothing)
