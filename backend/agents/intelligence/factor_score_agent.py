from backend.agents.base.category_bases import IntelligenceAgentBase
import numpy as np
from loguru import logger

agent_name = "factor_score_agent"


class FactorScoreAgent(IntelligenceAgentBase):
    async def _execute(self, symbol: str, agent_outputs: dict) -> dict:
        try:
            # Extract key factors from agent outputs
            factors = {
                "value": self._get_value_score(agent_outputs),
                "momentum": self._get_momentum_score(agent_outputs),
                "quality": self._get_quality_score(agent_outputs),
                "growth": self._get_growth_score(agent_outputs),
            }

            # Calculate composite score with regime-aware weights
            market_context = await self.get_market_context(symbol)
            regime = market_context.get("regime", "NEUTRAL")

            weights = self._get_regime_weights(regime)
            factor_score = sum(
                score * weights[factor] for factor, score in factors.items()
            )

            if factor_score > 0.7:
                verdict = "STRONG_FACTORS"
                confidence = 0.9
            elif factor_score > 0.5:
                verdict = "GOOD_FACTORS"
                confidence = 0.7
            else:
                verdict = "WEAK_FACTORS"
                confidence = 0.5

            return {
                "symbol": symbol,
                "verdict": verdict,
                "confidence": confidence,
                "value": round(factor_score, 4),
                "details": {
                    "factor_scores": {k: round(v, 4) for k, v in factors.items()},
                    "weights": weights,
                    "market_regime": regime,
                },
                "error": None,
                "agent_name": agent_name,
            }

        except Exception as e:
            logger.error(f"Factor score calculation error: {e}")
            return self._error_response(symbol, str(e))

    def _get_regime_weights(self, regime: str) -> dict:
        weights = {
            "BULL": {"value": 0.2, "momentum": 0.4, "quality": 0.2, "growth": 0.2},
            "BEAR": {"value": 0.4, "momentum": 0.2, "quality": 0.3, "growth": 0.1},
            "NEUTRAL": {"value": 0.3, "momentum": 0.3, "quality": 0.2, "growth": 0.2},
        }
        return weights.get(regime, weights["NEUTRAL"])

    def _get_value_score(self, outputs: dict) -> float:
        value_agents = ["pe_ratio_agent", "peg_ratio_agent", "pb_ratio_agent"]
        scores = [
            outputs.get(agent, {}).get("confidence", 0.0) for agent in value_agents
        ]
        return np.mean(scores) if scores else 0.0

    def _get_momentum_score(self, outputs: dict) -> float:
        momentum_agents = ["rsi_agent", "macd_agent", "momentum_agent"]
        scores = [
            outputs.get(agent, {}).get("confidence", 0.0) for agent in momentum_agents
        ]
        return np.mean(scores) if scores else 0.0

    def _get_quality_score(self, outputs: dict) -> float:
        quality_agents = ["risk_core_agent", "liquidity_agent"]
        scores = [
            outputs.get(agent, {}).get("confidence", 0.0) for agent in quality_agents
        ]
        return np.mean(scores) if scores else 0.0

    def _get_growth_score(self, outputs: dict) -> float:
        growth_agents = ["earnings_yield_agent", "peg_ratio_agent"]
        scores = [
            outputs.get(agent, {}).get("confidence", 0.0) for agent in growth_agents
        ]
        return np.mean(scores) if scores else 0.0


async def run(symbol: str, agent_outputs: dict = {}) -> dict:
    agent = FactorScoreAgent()
    return await agent.execute(symbol, agent_outputs)
