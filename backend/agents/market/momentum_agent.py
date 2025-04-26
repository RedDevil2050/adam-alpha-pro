from backend.agents.market.base import MarketAgentBase
from backend.utils.data_provider import fetch_price_series, fetch_volume_series
import numpy as np
import pandas as pd
from loguru import logger

agent_name = "momentum_agent"

class MomentumAgent(MarketAgentBase):
    async def _execute(self, symbol: str, agent_outputs: dict) -> dict:
        try:
            # Fetch price and volume data
            prices = await fetch_price_series(symbol)
            volumes = await fetch_volume_series(symbol)
            
            if not prices or len(prices) < 120:
                return self._error_response(symbol, "Insufficient price history")

            # Calculate momentum metrics
            returns = pd.Series(prices).pct_change()
            
            # Multiple timeframe momentum
            mom_20 = returns[-20:].sum()
            mom_60 = returns[-60:].sum()
            mom_120 = returns[-120:].sum()
            
            # Volume trend
            vol_trend = np.mean(volumes[-20:]) / np.mean(volumes[-60:]) - 1
            
            # Composite momentum score
            weights = [0.5, 0.3, 0.2]  # Higher weight to recent momentum
            momentum_score = (
                weights[0] * mom_20 + 
                weights[1] * mom_60 + 
                weights[2] * mom_120
            ) * (1 + max(vol_trend, 0))  # Volume trend adjustment
            
            # Market regime adjustment
            market_context = await self.get_market_context(symbol)
            regime = market_context.get('regime', 'NEUTRAL')
            
            # Generate verdict
            if momentum_score > 0.05:
                verdict = "STRONG_MOMENTUM"
                confidence = self.adjust_for_market_regime(0.9, regime)
            elif momentum_score > 0.02:
                verdict = "POSITIVE_MOMENTUM"
                confidence = self.adjust_for_market_regime(0.7, regime)
            elif momentum_score > -0.02:
                verdict = "NEUTRAL_MOMENTUM"
                confidence = 0.5
            elif momentum_score > -0.05:
                verdict = "NEGATIVE_MOMENTUM"
                confidence = self.adjust_for_market_regime(0.7, regime)
            else:
                verdict = "WEAK_MOMENTUM"
                confidence = self.adjust_for_market_regime(0.9, regime)

            return {
                "symbol": symbol,
                "verdict": verdict,
                "confidence": confidence,
                "value": round(momentum_score, 4),
                "details": {
                    "momentum_20d": round(mom_20, 4),
                    "momentum_60d": round(mom_60, 4),
                    "momentum_120d": round(mom_120, 4),
                    "volume_trend": round(vol_trend, 4),
                    "market_regime": regime
                },
                "error": None,
                "agent_name": agent_name
            }

        except Exception as e:
            logger.error(f"Momentum calculation error: {e}")
            return self._error_response(symbol, str(e))

async def run(symbol: str, agent_outputs: dict = {}) -> dict:
    agent = MomentumAgent()
    return await agent.execute(symbol, agent_outputs)
