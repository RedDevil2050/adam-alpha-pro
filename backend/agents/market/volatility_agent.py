from backend.agents.market.base import MarketAgentBase
from backend.utils.data_provider import fetch_price_series
import numpy as np
from loguru import logger

agent_name = "volatility_agent"

class VolatilityAgent(MarketAgentBase):
    async def _execute(self, symbol: str, agent_outputs: dict) -> dict:
        try:
            prices = await fetch_price_series(symbol)
            if not prices or len(prices) < 30:
                return self._error_response(symbol, "Insufficient price history")

            # Calculate rolling volatility metrics
            returns = np.diff(np.log(prices))
            vol_30d = np.std(returns[-30:]) * np.sqrt(252)
            vol_90d = np.std(returns[-90:]) * np.sqrt(252) if len(returns) >= 90 else vol_30d
            
            # Calculate historical percentile
            hist_vol = np.std(returns) * np.sqrt(252)
            vol_percentile = np.percentile(returns, 90)
            
            # Determine regime
            if vol_30d > vol_90d * 1.5:
                verdict = "HIGH_VOLATILITY"
                confidence = 0.9
            elif vol_30d < vol_90d * 0.5:
                verdict = "LOW_VOLATILITY"
                confidence = 0.8
            else:
                verdict = "NORMAL_VOLATILITY"
                confidence = 0.6

            return {
                "symbol": symbol,
                "verdict": verdict,
                "confidence": confidence,
                "value": round(vol_30d * 100, 2),
                "details": {
                    "volatility_30d": round(vol_30d * 100, 2),
                    "volatility_90d": round(vol_90d * 100, 2),
                    "historical_vol": round(hist_vol * 100, 2),
                    "vol_percentile": round(vol_percentile, 2)
                },
                "error": None,
                "agent_name": agent_name
            }

        except Exception as e:
            logger.error(f"Volatility calculation error: {e}")
            return self._error_response(symbol, str(e))

async def run(symbol: str, agent_outputs: dict = {}) -> dict:
    agent = VolatilityAgent()
    return await agent.execute(symbol, agent_outputs)
