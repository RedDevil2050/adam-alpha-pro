from backend.agents.base import AgentBase
from backend.agents.categories import CategoryType

class ValuationAgentBase(AgentBase):
    @property
    def category(self) -> CategoryType:
        return CategoryType.VALUATION

    def _adjust_for_fundamentals(self, value: float, fundamentals: dict) -> float:
        sector_premium = fundamentals.get('sector_premium', 1.0)
        growth_rate = fundamentals.get('growth_rate', 0.0)
        return value * (1 + growth_rate) * sector_premium

class TechnicalAgentBase(AgentBase):
    @property
    def category(self) -> CategoryType:
        return CategoryType.TECHNICAL

    def _adjust_for_volatility(self, signal: float, volatility: float) -> float:
        return signal * (1 - min(volatility, 0.5))

class MarketAgentBase(AgentBase):
    @property
    def category(self) -> CategoryType:
        return CategoryType.MARKET

    def _get_regime_thresholds(self) -> dict:
        return {
            'BULL': {'upper': 0.8, 'lower': 0.4},
            'BEAR': {'upper': 0.6, 'lower': 0.2},
            'NEUTRAL': {'upper': 0.7, 'lower': 0.3}
        }

class SentimentAgentBase(AgentBase):
    @property
    def category(self) -> CategoryType:
        return CategoryType.SENTIMENT

    def _normalize_sentiment(self, score: float) -> float:
        return max(0.0, min(1.0, (score + 1) / 2))

class RiskAgentBase(AgentBase):
    @property
    def category(self) -> CategoryType:
        return CategoryType.RISK

    def _calculate_risk_adjusted_return(self, returns: float, risk: float) -> float:
        return returns / max(risk, 0.01)

class EventAgentBase(AgentBase):
    @property
    def category(self) -> CategoryType:
        return CategoryType.EVENT

    def _calculate_event_impact(self, probability: float, magnitude: float) -> float:
        return probability * magnitude

class ESGAgentBase(AgentBase):
    @property
    def category(self) -> CategoryType:
        return CategoryType.ESG

    def _normalize_esg_score(self, score: float) -> float:
        return max(0.0, min(1.0, score / 100.0))

class IntelligenceAgentBase(AgentBase):
    @property
    def category(self) -> CategoryType:
        return CategoryType.INTELLIGENCE

    def _combine_signals(self, signals: List[float], weights: List[float] = None) -> float:
        if not weights:
            weights = [1.0/len(signals)] * len(signals)
        return sum(s * w for s, w in zip(signals, weights))

class MacroAgentBase(AgentBase):
    @property
    def category(self) -> CategoryType:
        return CategoryType.MACRO

    def _adjust_for_macro(self, value: float, macro_indicators: dict) -> float:
        gdp_growth = macro_indicators.get('gdp_growth', 0.0)
        inflation = macro_indicators.get('inflation', 0.0)
        return value * (1 + gdp_growth - inflation)

class StealthAgentBase(AgentBase):
    @property
    def category(self) -> CategoryType:
        return CategoryType.STEALTH

    async def _fetch_stealth_data(self, symbol: str) -> dict:
        """Implement in derived classes"""
        raise NotImplementedError
