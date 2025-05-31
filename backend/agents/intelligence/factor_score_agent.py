from backend.agents.base.category_bases import IntelligenceAgentBase
import numpy as np
from loguru import logger  # Module-level logger
from backend.agents.decorators import standard_agent_execution  # Added
from backend.config.settings import AgentSettings  # Added for type hinting
from backend.data.providers.base_provider import BaseDataProvider  # Added for type hinting
from typing import Any  # Added

agent_name = "factor_score_agent"
AGENT_CATEGORY = "INTELLIGENCE"  # Added category


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

            # Prepare details dictionary
            details_dict = {
                "factor_scores": factors,
                "market_regime": regime,
                "weights": weights,
                "value": factor_score,  # Composite score
            }

            return {
                "verdict": verdict,
                "confidence": confidence,
                "details": details_dict,
                # Fields like 'symbol', 'agent_name', 'error' are handled by AgentBase or _format_output
            }

        except Exception as e:
            self.logger.error(f"Factor score calculation error: {e}")
            # _error_response is part of AgentBase, which will be called by the execute method if an exception bubbles up
            # For direct calls or specific handling, ensure it matches AgentBase._error_response structure
            # or rely on AgentBase's error handling.
            # For now, let the exception propagate to be handled by AgentBase.execute's try-except.
            raise  # Propagate error to be handled by AgentBase

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


@standard_agent_execution(agent_name=agent_name, category=AGENT_CATEGORY)  # Added category argument
async def run(
    symbol: str,
    agent_outputs: dict = {},
    *,  # Enforce keyword arguments for injected dependencies
    name: str,  # Injected by decorator, will be 'factor_score_agent'
    settings: AgentSettings,
    logger: Any,  # Injected logger instance
    cache_client: Any,
    data_provider: BaseDataProvider,
    market_context_provider: Any,
    **kwargs  # To catch any other args
) -> dict:
    agent = FactorScoreAgent(
        name=name,  # Use the name from the decorator
        settings=settings,
        logger=logger,
        cache_client=cache_client,
        data_provider=data_provider,
        market_context_provider=market_context_provider,
    )
    return await agent.execute(symbol, agent_outputs=agent_outputs)
