from backend.agents.technical.base import TechnicalAgent
from backend.utils.data_provider import fetch_ohlcv_series
import numpy as np
from loguru import logger

agent_name = "trend_strength_agent"


class TrendStrengthAgent(TechnicalAgent):
    async def _execute(self, symbol: str, agent_outputs: dict) -> dict:
        try:
            df = await fetch_ohlcv_series(symbol)
            if df is None or df.empty:
                return self._error_response(symbol, "No data available")

            # Calculate trend metrics
            close = df["close"]
            sma20 = close.rolling(window=20).mean()
            sma50 = close.rolling(window=50).mean()

            # Directional strength
            direction = 1 if sma20.iloc[-1] > sma50.iloc[-1] else -1
            slope20 = (sma20.iloc[-1] - sma20.iloc[-20]) / sma20.iloc[-20]
            slope50 = (sma50.iloc[-1] - sma50.iloc[-20]) / sma50.iloc[-20]

            # Volume trend confirmation
            volume = df["volume"]
            vol_sma = volume.rolling(window=20).mean()
            vol_trend = volume.iloc[-1] > vol_sma.iloc[-1]

            # Combine metrics for strength score
            strength_score = abs(slope20) * (1.5 if direction * slope20 > 0 else 0.5)
            if vol_trend and direction * slope20 > 0:
                strength_score *= 1.2

            # Market regime adjustment
            market_context = await self.get_market_context(symbol)
            regime = market_context.get("regime", "NEUTRAL")

            # Determine verdict based on strength and direction
            if strength_score > 0.02:
                verdict = "STRONG_UPTREND" if direction > 0 else "STRONG_DOWNTREND"
                confidence = self.adjust_for_market_regime(0.8, regime)
            elif strength_score > 0.01:
                verdict = "WEAK_UPTREND" if direction > 0 else "WEAK_DOWNTREND"
                confidence = self.adjust_for_market_regime(0.6, regime)
            else:
                verdict = "NO_TREND"
                confidence = 0.4

            return {
                "symbol": symbol,
                "verdict": verdict,
                "confidence": confidence,
                "value": round(strength_score * direction, 4),
                "details": {
                    "strength_score": round(strength_score, 4),
                    "direction": direction,
                    "slope20": round(slope20, 4),
                    "slope50": round(slope50, 4),
                    "volume_confirms": vol_trend,
                    "market_regime": regime,
                },
                "error": None,
                "agent_name": agent_name,
            }

        except Exception as e:
            logger.error(f"Trend strength calculation error: {e}")
            return self._error_response(symbol, str(e))


async def run(symbol: str, agent_outputs: dict = {}) -> dict:
    agent = TrendStrengthAgent()
    return await agent.execute(symbol, agent_outputs)
