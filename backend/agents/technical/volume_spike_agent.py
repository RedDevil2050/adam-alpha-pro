from backend.agents.technical.base import TechnicalAgent
from backend.utils.data_provider import fetch_ohlcv_series
import numpy as np
from loguru import logger
from datetime import datetime, timedelta

agent_name = "volume_spike_agent"


class VolumeSpikeAgent(TechnicalAgent):
    async def _execute(self, symbol: str, agent_outputs: dict) -> dict:
        try:
            # Define date range for the past year
            end_date = datetime(2025, 4, 30)
            start_date = end_date - timedelta(days=365)
            end_date_str = end_date.strftime('%Y-%m-%d')
            start_date_str = start_date.strftime('%Y-%m-%d')

            df = await fetch_ohlcv_series(symbol, start_date=start_date_str, end_date=end_date_str)
            if df is None or df.empty:
                return self._error_response(symbol, "No data available")

            # Calculate volume metrics
            avg_volume = df["volume"].rolling(window=20).mean()
            volume_ratio = df["volume"] / avg_volume
            latest_ratio = volume_ratio.iloc[-1]

            # Determine if price moved with volume
            price_change = (df["close"].iloc[-1] - df["open"].iloc[-1]) / df[
                "open"
            ].iloc[-1]

            # Market regime context
            market_context = await self.get_market_context(symbol)
            regime = market_context.get("regime", "NEUTRAL")

            # Score and verdict logic
            if latest_ratio > 2.0:  # Volume spike detected
                if price_change > 0:
                    verdict = "BULLISH_VOLUME"
                    confidence = self.adjust_for_market_regime(0.8, regime)
                else:
                    verdict = "BEARISH_VOLUME"
                    confidence = self.adjust_for_market_regime(0.7, regime)
            else:
                verdict = "NORMAL_VOLUME"
                confidence = 0.5

            return {
                "symbol": symbol,
                "verdict": verdict,
                "confidence": confidence,
                "value": round(latest_ratio, 2),
                "details": {
                    "volume_ratio": round(latest_ratio, 2),
                    "price_change": round(price_change * 100, 2),
                    "market_regime": regime,
                },
                "error": None,
                "agent_name": agent_name,
            }

        except Exception as e:
            logger.error(f"Volume spike calculation error: {e}")
            return self._error_response(symbol, str(e))


async def run(symbol: str, agent_outputs: dict = {}) -> dict:
    agent = VolumeSpikeAgent()
    return await agent.execute(symbol, agent_outputs)
