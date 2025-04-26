from backend.agents.risk.base import RiskAgentBase
from backend.utils.data_provider import fetch_price_series
import numpy as np
from loguru import logger

agent_name = "risk_core_agent"

class RiskCoreAgent(RiskAgentBase):
    async def _execute(self, symbol: str, agent_outputs: dict) -> dict:
        try:
            prices = await fetch_price_series(symbol)
            if not prices or len(prices) < 252:  # 1 year of data
                return self._error_response(symbol, "Insufficient price history")

            returns = np.diff(np.log(prices))
            
            # Calculate risk metrics
            volatility = np.std(returns) * np.sqrt(252)  # Annualized volatility
            skewness = self._calculate_skewness(returns)
            kurtosis = self._calculate_kurtosis(returns)
            max_drawdown = self._calculate_max_drawdown(prices)
            
            # Composite risk score (0-1, higher means lower risk)
            vol_score = 1 - min(volatility / 0.4, 1)  # Cap at 40% volatility
            skew_score = (skewness + 1) / 2  # Normalize -1 to 1 range
            kurt_score = 1 / (1 + kurtosis)  # Higher kurtosis = higher risk
            dd_score = 1 - min(abs(max_drawdown), 1)
            
            risk_score = np.mean([vol_score, skew_score, kurt_score, dd_score])

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
                "value": round(volatility * 100, 2),
                "details": {
                    "volatility": round(volatility * 100, 2),
                    "skewness": round(skewness, 2),
                    "kurtosis": round(kurtosis, 2),
                    "max_drawdown": round(max_drawdown * 100, 2)
                },
                "error": None,
                "agent_name": agent_name
            }

        except Exception as e:
            logger.error(f"Risk core calculation error: {e}")
            return self._error_response(symbol, str(e))

    def _calculate_skewness(self, returns):
        return float(np.nan_to_num(np.mean((returns - np.mean(returns))**3) / np.std(returns)**3))

    def _calculate_kurtosis(self, returns):
        return float(np.nan_to_num(np.mean((returns - np.mean(returns))**4) / np.std(returns)**4))

    def _calculate_max_drawdown(self, prices):
        running_max = np.maximum.accumulate(prices)
        drawdowns = (prices - running_max) / running_max
        return float(np.min(drawdowns))

async def run(symbol: str, agent_outputs: dict = {}) -> dict:
    agent = RiskCoreAgent()
    return await agent.execute(symbol, agent_outputs)
