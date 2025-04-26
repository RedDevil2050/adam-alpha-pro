from backend.agents.market.base import MarketAgentBase
from backend.utils.data_provider import fetch_price_series, fetch_volume_series
import numpy as np
from loguru import logger

agent_name = "liquidity_agent"

class LiquidityAgent(MarketAgentBase):
    async def _execute(self, symbol: str, agent_outputs: dict) -> dict:
        try:
            # Get price and volume data
            prices = await fetch_price_series(symbol)
            volumes = await fetch_volume_series(symbol)
            
            if not prices or not volumes or len(prices) < 20:
                return self._error_response(symbol, "Insufficient data")

            # Calculate liquidity metrics
            avg_daily_volume = np.mean(volumes[-20:])
            turnover = volumes[-1] * prices[-1]
            rel_volume = volumes[-1] / avg_daily_volume
            
            # Calculate spread proxy using high-low ratio
            spread_proxy = np.mean([(h-l)/c for h,l,c in zip(prices[-5:], prices[-5:], prices[-5:])])

            # Composite liquidity score (0-1)
            volume_score = min(1.0, rel_volume / 2)  # Normalize relative volume
            spread_score = max(0.0, 1 - spread_proxy*10)  # Lower spread is better
            liquidity_score = (volume_score + spread_score) / 2

            if liquidity_score > 0.7:
                verdict = "HIGH_LIQUIDITY"
                confidence = 0.9
            elif liquidity_score > 0.3:
                verdict = "MODERATE_LIQUIDITY"
                confidence = 0.6
            else:
                verdict = "LOW_LIQUIDITY"
                confidence = 0.3

            return {
                "symbol": symbol,
                "verdict": verdict,
                "confidence": confidence,
                "value": round(liquidity_score, 4),
                "details": {
                    "avg_daily_volume": int(avg_daily_volume),
                    "relative_volume": round(rel_volume, 2),
                    "turnover": int(turnover),
                    "spread_proxy": round(spread_proxy, 4)
                },
                "error": None,
                "agent_name": agent_name
            }

        except Exception as e:
            logger.error(f"Liquidity calculation error: {e}")
            return self._error_response(symbol, str(e))

async def run(symbol: str, agent_outputs: dict = {}) -> dict:
    agent = LiquidityAgent()
    return await agent.execute(symbol, agent_outputs)
