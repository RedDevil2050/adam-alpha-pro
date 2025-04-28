from typing import Dict, List
from dataclasses import dataclass
from enum import Enum
import importlib
from typing import Type


class CategoryType(Enum):
    VALUATION = "valuation"
    TECHNICAL = "technical"
    MARKET = "market"
    SENTIMENT = "sentiment"
    RISK = "risk"
    MACRO = "macro"
    EVENT = "event"
    ESG = "esg"
    INTELLIGENCE = "intelligence"
    STEALTH = "stealth"
    AUTOMATION = "automation"


@dataclass
class CategoryMetadata:
    name: str
    weight: float
    description: str
    required: bool = False
    dependencies: List[str] = None


class CategoryManager:
    CATEGORY_METADATA: Dict[CategoryType, CategoryMetadata] = {
        CategoryType.VALUATION: CategoryMetadata(
            name="Valuation",
            weight=0.25,
            description="Fundamental valuation metrics",
            required=True,
            dependencies=[],
        ),
        CategoryType.TECHNICAL: CategoryMetadata(
            name="Technical",
            weight=0.20,
            description="Technical analysis indicators",
            required=True,
            dependencies=[],
        ),
        CategoryType.MARKET: CategoryMetadata(
            name="Market",
            weight=0.15,
            description="Market regime and conditions",
            required=True,
            dependencies=[],
        ),
        CategoryType.SENTIMENT: CategoryMetadata(
            name="Sentiment",
            weight=0.10,
            description="Market sentiment analysis",
            dependencies=["MARKET"],
        ),
        CategoryType.RISK: CategoryMetadata(
            name="Risk",
            weight=0.10,
            description="Risk metrics and analysis",
            required=True,
            dependencies=["MARKET", "TECHNICAL"],
        ),
        CategoryType.MACRO: CategoryMetadata(
            name="Macro",
            weight=0.05,
            description="Macroeconomic indicators",
            dependencies=[],
        ),
        CategoryType.EVENT: CategoryMetadata(
            name="Event",
            weight=0.05,
            description="Corporate events and actions",
            dependencies=[],
        ),
        CategoryType.ESG: CategoryMetadata(
            name="ESG",
            weight=0.05,
            description="Environmental, Social, Governance",
            dependencies=[],
        ),
        CategoryType.INTELLIGENCE: CategoryMetadata(
            name="Intelligence",
            weight=0.05,
            description="AI-powered analysis",
            dependencies=["VALUATION", "TECHNICAL", "SENTIMENT"],
        ),
    }

    _agent_registry: Dict[CategoryType, List[str]] = {
        CategoryType.VALUATION: [
            "pe_ratio_agent",
            "peg_ratio_agent",
            "price_to_sales_agent",
            "pfcf_ratio_agent",
            "pb_ratio_agent",
            "ev_ebitda_agent",
            "book_to_market_agent",
            "earnings_yield_agent",
            "dcf_agent",
            "reverse_dcf_agent",
            "intrinsic_composite_agent",
            "price_target_agent",
            "dividend_yield_agent",
        ],
        CategoryType.TECHNICAL: [
            "rsi_agent",
            "macd_agent",
            "moving_average_agent",
            "bollinger_agent",
            "adx_agent",
            "trend_strength_agent",
            "ma_crossover_agent",
            "volume_spike_agent",
            "stochastic_agent",
            "supertrend_agent",
        ],
        CategoryType.MARKET: [
            "market_regime_agent",
            "volatility_agent",
            "liquidity_agent",
            "correlation_agent",
            "momentum_agent",
        ],
        CategoryType.SENTIMENT: [
            "news_sentiment_agent",
            "social_sentiment_agent",
            "nlp_topic_agent",
        ],
        CategoryType.RISK: [
            "beta_agent",
            "var_agent",
            "risk_core_agent",
            "portfolio_risk_agent",
        ],
        CategoryType.MACRO: [
            "interest_rate_agent",
            "inflation_agent",
            "gdp_growth_agent",
        ],
        CategoryType.EVENT: [
            "earnings_agent",
            "corporate_actions_agent",
            "share_buyback_agent",
        ],
        CategoryType.ESG: [
            "environmental_agent",
            "social_agent",
            "governance_agent",
            "composite_esg_agent",
        ],
        CategoryType.INTELLIGENCE: [
            "composite_valuation_agent",
            "target_price_agent",
            "theme_match_agent",
            "peer_compare_agent",
            "factor_score_agent",
            "ask_alpha_agent",
            "ask_adam_agent",
        ],
        CategoryType.STEALTH: [
            "zerodha_agent",
            "trendlyne_agent",
            "tradingview_agent",
            "tickertape_agent",
            "stockedge_agent",
            "moneycontrol_agent",
        ],
        CategoryType.AUTOMATION: [
            "bulk_portfolio_agent",
            "auto_watchlist_agent",
            "alert_engine_agent",
        ],
    }

    @classmethod
    async def get_category_agents(cls, category: CategoryType) -> List[Type]:
        """Get all agent classes for a category"""
        agents = []
        for agent_name in cls._agent_registry.get(category, []):
            try:
                module = importlib.import_module(
                    f"backend.agents.{category.value}.{agent_name}"
                )
                if hasattr(module, "run"):
                    agents.append(module.run)
            except ImportError:
                continue
        return agents

    @classmethod
    async def execute_category(
        cls, category: CategoryType, symbol: str, context: Dict = None
    ) -> List[Dict]:
        """Execute all agents in a category"""
        agents = await cls.get_category_agents(category)
        results = []
        for agent in agents:
            try:
                result = await agent(symbol, context or {})
                if result:
                    results.append(result)
            except Exception as e:
                logger.error(f"Agent execution failed: {e}")
        return results

    @classmethod
    def validate_category_result(
        cls, category: CategoryType, results: List[Dict]
    ) -> bool:
        """Validate category execution results"""
        if not results:
            return False
        metadata = cls.CATEGORY_METADATA[category]
        if (
            metadata.required
            and len(results) < len(cls._agent_registry[category]) * 0.5
        ):
            return False
        return True

    @classmethod
    def get_category_weight(cls, category: CategoryType) -> float:
        return cls.CATEGORY_METADATA[category].weight

    @classmethod
    def get_required_categories(cls) -> List[CategoryType]:
        return [cat for cat in CategoryType if cls.CATEGORY_METADATA[cat].required]

    @classmethod
    def get_dependencies(cls, category: CategoryType) -> List[CategoryType]:
        return cls.CATEGORY_METADATA[category].dependencies
