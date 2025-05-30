from backend.agents.technical.base import TechnicalAgent
import pandas as pd
import numpy as np
import datetime  # Import datetime
from typing import Any  # Add Any for type hinting

from backend.agents.decorators import standard_agent_execution  # Added
from backend.config.settings import AgentSettings  # Added
from backend.data.providers.base_provider import BaseDataProvider  # Added

agent_name = "macd_agent"
AGENT_CATEGORY = "TECHNICAL"  # Added


class MACDAgent(TechnicalAgent):
    async def _execute(self, symbol: str, agent_outputs: dict) -> dict:
        try:
            # Define date range (e.g., 1 year back from today)
            end_date = datetime.date.today()
            start_date = end_date - datetime.timedelta(days=365)

            # Add await here and pass dates
            df = await self.data_provider.get_ohlcv(symbol, start_date=start_date, end_date=end_date)  # Changed to use self.data_provider
            # Add check for DataFrame type and emptiness
            if not isinstance(df, pd.DataFrame) or df.empty:
                # logger.warning(f\"[{agent_name}] Insufficient or invalid data for {symbol}. Type: {type(df)}\") # Old line
                self.logger.warning(f"[{agent_name}] Insufficient or invalid data for {symbol}. Type: {type(df)}")  # Changed to self.logger
                return self._error_response(symbol, f"Insufficient or invalid OHLCV data received. Type: {type(df)}")

            # Calculate MACD
            exp1 = df["close"].ewm(span=12, adjust=False).mean()
            exp2 = df["close"].ewm(span=26, adjust=False).mean()
            macd = exp1 - exp2
            signal = macd.ewm(span=9, adjust=False).mean()
            histogram = macd - signal

            # Get latest values
            current_macd = macd.iloc[-1]
            current_signal = signal.iloc[-1]
            current_hist = histogram.iloc[-1]

            # Market regime adjustment
            market_context = await self.get_market_context(symbol)
            regime = market_context.get("regime", "NEUTRAL")

            # Generate signals
            if current_macd > current_signal and current_hist > 0:
                verdict = "BUY"
                confidence = self.adjust_for_market_regime(0.8, regime)
            elif current_macd < current_signal and current_hist < 0:
                verdict = "SELL"
                confidence = self.adjust_for_market_regime(0.8, regime)
            else:
                verdict = "HOLD"
                confidence = 0.5

            return {
                "symbol": symbol,
                "verdict": verdict,
                "confidence": confidence,
                "value": round(current_macd, 4),
                "details": {
                    "macd": round(current_macd, 4),
                    "signal": round(current_signal, 4),
                    "histogram": round(current_hist, 4),
                    "market_regime": regime,
                },
                "error": None,
                "agent_name": agent_name,
            }

        except Exception as e:
            # logger.error(f\"MACD calculation error: {e}\") # Old line
            self.logger.error(f"MACD calculation error: {e}")  # Changed to self.logger
            return self._error_response(symbol, str(e))


@standard_agent_execution(agent_name=agent_name, category=AGENT_CATEGORY)  # Added decorator
async def run(symbol: str, agent_outputs: dict = None, name: str = None, settings: AgentSettings = None, logger: Any = None, cache_client: Any = None, data_provider: BaseDataProvider = None, market_context_provider: Any = None) -> dict:  # Modified signature
    # agent = MACDAgent() # Old instantiation
    agent = MACDAgent(  # New instantiation with all args
        name=name,
        settings=settings,
        logger=logger,
        cache_client=cache_client,
        data_provider=data_provider,
        market_context_provider=market_context_provider
    )
    # Add await here
    return await agent.execute(symbol, agent_outputs)
