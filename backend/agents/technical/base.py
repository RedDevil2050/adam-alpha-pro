from backend.agents.base import AgentBase
from backend.agents.categories import CategoryType

class TechnicalAgent(AgentBase):
    @property
    def category(self) -> CategoryType:
        return CategoryType.TECHNICAL

    def get_volatility_adjustments(self, volatility: float) -> dict:
        if volatility > 0.3:
            return {'signal_mult': 0.7, 'period_adj': 1.5}
        elif volatility > 0.2:
            return {'signal_mult': 0.85, 'period_adj': 1.25}
        return {'signal_mult': 1.0, 'period_adj': 1.0}
