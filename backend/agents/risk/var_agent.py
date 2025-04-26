from backend.agents.risk.base import RiskAgentBase
from backend.utils.data_provider import fetch_price_series
import numpy as np
from loguru import logger

agent_name = "var_agent"

class VaRAgent(RiskAgentBase):
    async def _execute(self, symbol: str, agent_outputs: dict) -> dict:
        try:
            prices = await fetch_price_series(symbol)
            if not prices or len(prices) < 60:
                return self._error_response(symbol, "Insufficient price history")

            returns = np.diff(np.log(prices))
            var_95 = np.percentile(returns, 5)
            var_99 = np.percentile(returns, 1)
            
            # Annualize
            var_95_annual = var_95 * np.sqrt(252)
            var_99_annual = var_99 * np.sqrt(252)

            # Normalize to score
            risk_score = min(1.0, max(0.0, 1.0 + var_95_annual))
            
            if risk_score > 0.7:
                verdict = "LOW_RISK"
            elif risk_score > 0.4:
                verdict = "MODERATE_RISK"
            else:
                verdict = "HIGH_RISK"

            return {
                "symbol": symbol,
                "verdict": verdict,
                "confidence": round(risk_score, 4),
                "value": round(-var_95_annual * 100, 2),
                "details": {
                    "var_95": round(-var_95_annual * 100, 2),
                    "var_99": round(-var_99_annual * 100, 2),
                    "days": len(prices)
                },
                "error": None,
                "agent_name": agent_name
            }

        except Exception as e:
            logger.error(f"VaR calculation error: {e}")
            return self._error_response(symbol, str(e))

# For backwards compatibility
async def run(symbol: str, agent_outputs: dict = {}) -> dict:
    agent = VaRAgent()
    return await agent.execute(symbol, agent_outputs)
