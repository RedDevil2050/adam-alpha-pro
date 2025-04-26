from backend.agents.base import AgentBase
from backend.agents.categories import CategoryType

class ValuationAgent(AgentBase):
    @property
    def category(self) -> CategoryType:
        return CategoryType.VALUATION

    def get_regime_adjustments(self, regime: str) -> dict:
        return {
            'BULL': {'multiplier': 1.2, 'threshold': 1.1},
            'BEAR': {'multiplier': 0.8, 'threshold': 0.9},
            'NEUTRAL': {'multiplier': 1.0, 'threshold': 1.0},
            'VOLATILE': {'multiplier': 0.7, 'threshold': 0.8}
        }.get(regime, {'multiplier': 1.0, 'threshold': 1.0})
