from backend.agents.technical.base import TechnicalAgent
import pandas as pd
import numpy as np
import datetime  # Import datetime
from typing import Any  # Add Any for type hinting

from backend.agents.decorators import standard_agent_execution  # Added
from backend.config.settings import AgentSettings  # Added
from backend.data.providers.base_provider import BaseDataProvider  # Added
from backend.models.common_models import Verdict, VerdictType # Added

agent_name = "macd_agent"
AGENT_CATEGORY = "TECHNICAL"  # Added


class MACDAgent(TechnicalAgent):
    REQUIRED_HISTORY_DAYS = 365  # Added class attribute

    async def _execute(self, symbol: str, agent_outputs: dict) -> Verdict: # Changed return type
        try:
            # Define date range (e.g., 1 year back from today)
            end_date = datetime.date.today()
            # MODIFIED: Use REQUIRED_HISTORY_DAYS from class attribute
            start_date = end_date - datetime.timedelta(days=self.REQUIRED_HISTORY_DAYS) 

            # Add await here and pass dates
            # MODIFIED: Changed get_ohlcv to fetch_price_data, pass interval
            df = await self.data_provider.fetch_price_data(symbol, start_date=start_date, end_date=end_date, interval="1d")
            # Add check for DataFrame type and emptiness
            if not isinstance(df, pd.DataFrame) or df.empty:
                self.logger.warning(f"[{agent_name}] Insufficient or invalid data for {symbol}. Type: {type(df)}")
                return Verdict(
                    verdict=VerdictType.ERROR,
                    confidence=0.0,
                    agent_name=agent_name,
                    details={"error": f"Insufficient or invalid OHLCV data received. Type: {type(df)}", "symbol": symbol},
                    value=None
                )

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
            verdict_str = ""
            if current_macd > current_signal and current_hist > 0:
                verdict_str = "BUY"
                confidence = self.adjust_for_market_regime(0.8, regime)
            elif current_macd < current_signal and current_hist < 0:
                verdict_str = "SELL"
                confidence = self.adjust_for_market_regime(0.8, regime)
            else:
                verdict_str = "HOLD"
                confidence = 0.5
            
            verdict_val = VerdictType[verdict_str] # Convert string to VerdictType

            return Verdict(
                verdict=verdict_val,
                confidence=confidence,
                value=round(current_macd, 4),
                details={
                    "macd": round(current_macd, 4),
                    "signal": round(current_signal, 4),
                    "histogram": round(current_hist, 4),
                    "market_regime": regime,
                    "symbol": symbol, 
                },
                agent_name=agent_name
            )

        except Exception as e:
            self.logger.error(f"MACD calculation error: {e}")
            return Verdict(
                verdict=VerdictType.ERROR,
                confidence=0.0,
                agent_name=agent_name,
                details={"error": str(e), "symbol": symbol},
                value=None
            )


@standard_agent_execution(agent_name=agent_name, category=AGENT_CATEGORY)
async def run(symbol: str, agent_outputs: dict = None, name: str = None, settings: AgentSettings = None, logger: Any = None, cache_client: Any = None, data_provider: BaseDataProvider = None, market_context_provider: Any = None) -> Verdict: # Modified signature to return Verdict
    agent = MACDAgent(
        name=name,
        settings=settings,
        logger=logger,
        cache_client=cache_client,
        data_provider=data_provider,
        market_context_provider=market_context_provider
    )
    return await agent.execute(symbol, agent_outputs)
