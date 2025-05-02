from backend.agents.technical.base import TechnicalAgent
# Correct the import path
from backend.utils.data_provider import fetch_ohlcv_series
from backend.agents.decorators import standard_agent_execution  # Corrected import path
import pandas as pd
import logging
import numpy as np # Import numpy

logger = logging.getLogger(__name__)

# Add agent_name at module level
agent_name = "RSIAgent"

class RSIAgent(TechnicalAgent):
    async def _execute(self, symbol: str, agent_outputs: dict) -> dict:
        try:
            # Add await here
            df = await fetch_ohlcv_series(symbol)
            # Add check for DataFrame type and emptiness
            if not isinstance(df, pd.DataFrame) or df.empty:
                logger.warning(f"[{self.__class__.__name__}] Insufficient or invalid data for {symbol}. Type: {type(df)}")
                return self._error_response(symbol, f"Insufficient or invalid OHLCV data received. Type: {type(df)}")

            # Ensure 'close' column exists
            if 'close' not in df.columns:
                 logger.error(f"[{self.__class__.__name__}] 'close' column not found in data for {symbol}.")
                 return self._error_response(symbol, "'close' column not found in OHLCV data.")

            # Add await here
            market_context = await self.get_market_context(symbol)
            volatility = market_context.get("volatility", 0.2)
            adjustments = self.get_volatility_adjustments(volatility)

            # Calculate RSI using the new method
            rsi_value = self._calculate_rsi(
                df["close"], period=int(14 * adjustments["period_adj"])
            )

            # Check if RSI calculation was successful
            if rsi_value is None:
                logger.warning(f"[{self.__class__.__name__}] RSI calculation failed for {symbol}, likely insufficient data.")
                return self._error_response(symbol, "RSI calculation failed (insufficient data).")

            # Adjust signals based on market regime
            signals = self._get_regime_signals(
                rsi_value, market_context.get("regime", "NEUTRAL") # Use rsi_value
            )

            return {
                "symbol": symbol,
                "verdict": signals["verdict"],
                "confidence": signals["confidence"],
                "value": round(rsi_value, 2), # Use rsi_value
                "details": {
                    "rsi": round(rsi_value, 2), # Use rsi_value
                    "market_regime": market_context.get("regime"),
                },
                "error": None,
                "agent_name": self.__class__.__name__,
            }

        except Exception as e:
            logger.exception(f"[{self.__class__.__name__}] Error executing agent for {symbol}: {e}") # Log exception
            return self._error_response(symbol, str(e))

    # --- Added _calculate_rsi method ---
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float | None:
        """Calculates the Relative Strength Index (RSI) for a given price series."""
        if prices is None or len(prices) < period + 1:
            return None # Not enough data

        delta = prices.diff()

        # Separate gains (positive changes) and losses (absolute value of negative changes)
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0) # Use -delta to make losses positive

        # Calculate the exponential moving average (EMA) of gains and losses
        # Use adjust=False to match common RSI implementations (like TradingView)
        avg_gain = gain.ewm(com=period - 1, min_periods=period, adjust=False).mean()
        avg_loss = loss.ewm(com=period - 1, min_periods=period, adjust=False).mean()

        # Avoid division by zero
        if avg_loss.iloc[-1] == 0:
            # If avg loss is 0, RSI is 100 (unless avg gain is also 0)
            return 100.0 if avg_gain.iloc[-1] > 0 else 50.0 # Or 50 if both are 0

        # Calculate Relative Strength (RS)
        rs = avg_gain.iloc[-1] / avg_loss.iloc[-1]

        # Calculate RSI
        rsi = 100.0 - (100.0 / (1.0 + rs))

        # Return the latest RSI value, checking for NaN
        return rsi if not np.isnan(rsi) else None
    # --- End Added Method ---

    def _get_regime_signals(self, rsi: float, regime: str) -> dict:
        base_oversold = 30
        base_overbought = 70

        regime_adjustments = {
            "BULL": {"oversold": 35, "overbought": 75},
            "BEAR": {"oversold": 25, "overbought": 65},
            "VOLATILE": {"oversold": 20, "overbought": 80},
        }

        levels = regime_adjustments.get(
            regime, {"oversold": base_oversold, "overbought": base_overbought}
        )

        if rsi < levels["oversold"]:
            return {
                "verdict": "BUY",
                "confidence": self.adjust_for_market_regime(0.8, regime),
            }
        elif rsi > levels["overbought"]:
            return {
                "verdict": "SELL",
                "confidence": self.adjust_for_market_regime(0.8, regime),
            }
        return {"verdict": "HOLD", "confidence": 0.5}


# For backwards compatibility
# Apply the standard decorator
@standard_agent_execution(agent_name=agent_name, category="technical", cache_ttl=3600)
async def run(symbol: str, agent_outputs: dict = {}) -> dict:
    agent = RSIAgent()
    # The decorator now handles execution, caching, errors, etc.
    # We just need the core logic call here.
    # The decorator passes args/kwargs, so we need to adjust the call slightly
    # or rely on the decorator passing the symbol correctly.
    # Assuming the decorator passes symbol as the first arg to the wrapped execute.
    # Let's simplify: the decorator wraps the agent's execute method directly if possible,
    # or we adapt the run function. Let's stick to decorating run for now.
    # The agent instance needs to be created inside the decorated function.
    # The decorator expects the decorated function to perform the core logic.
    # Let's refactor slightly: the decorated function will *be* the core logic.

    # Refactored: The decorated function IS the core logic execution
    # The RSIAgent class logic might need adjustment if it relies on self state
    # across calls, but typically agents are stateless per call.
    # Let's assume RSIAgent._execute can be called.
    # This requires rethinking the structure slightly. How is TechnicalAgent used?
    # Let's revert to the simpler approach: Decorate the existing run function.
    # The decorator will call this run function.
    # The run function then calls agent.execute.

    # Re-applying decorator to the existing run structure:
    agent = RSIAgent()
    # The decorator expects func(symbol, *args, **kwargs)
    # Our run takes (symbol, agent_outputs={}). Let's assume agent_outputs isn't used by decorator.
    return await agent.execute(symbol, agent_outputs)
