from backend.agents.technical.base import TechnicalAgent
from backend.utils.data_provider import fetch_ohlcv_series
import pandas as pd
import numpy as np
from loguru import logger

agent_name = "macd_agent"


class MACDAgent(TechnicalAgent):
    async def _execute(self, symbol: str, agent_outputs: dict) -> dict:
        try:
            df = await fetch_ohlcv_series(symbol)
            if df is None or df.empty:
                return self._error_response(symbol, "No data available")

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
            logger.error(f"MACD calculation error: {e}")
            return self._error_response(symbol, str(e))


async def run(symbol: str, agent_outputs: dict = {}) -> dict:
    agent = MACDAgent()
    return await agent.execute(symbol, agent_outputs)
