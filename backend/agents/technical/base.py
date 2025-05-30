from abc import abstractmethod
from backend.agents.base import AgentBase
from backend.agents.categories import CategoryType
from backend.config.settings import AgentSettings  # Added
from backend.data.providers.base_provider import BaseDataProvider  # Added
from typing import Any  # Added


class TechnicalAgent(AgentBase):
    def __init__(self, name: str, settings: AgentSettings, logger: Any, cache_client: Any, data_provider: BaseDataProvider, market_context_provider: Any, **kwargs):
        super().__init__(name=name, settings=settings, logger=logger, cache_client=cache_client, data_provider=data_provider, market_context_provider=market_context_provider, **kwargs)
        # Any TechnicalAgent-specific initialization can go here if needed in the future

    @property
    def category(self) -> CategoryType:
        return CategoryType.TECHNICAL

    @abstractmethod
    async def _execute(self, symbol: str, agent_outputs: dict) -> dict:
        """Abstract method to be implemented by all technical agents."""
        pass

    def get_volatility_adjustments(self, volatility: float) -> dict:
        if volatility > 0.3:
            return {"signal_mult": 0.7, "period_adj": 1.5}
        elif volatility > 0.2:
            return {"signal_mult": 0.85, "period_adj": 1.25}
        return {"signal_mult": 1.0, "period_adj": 1.0}
