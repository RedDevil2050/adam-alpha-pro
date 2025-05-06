from typing import Dict, List
from dataclasses import dataclass
from enum import Enum
import importlib
from typing import Type
import logging

logger = logging.getLogger(__name__)


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
            "market_regime_agent", # Uncommented
            "volatility_agent",
            # "liquidity_agent", # Removed - Missing fetch_volume_series
            "correlation_agent",
            # "momentum_agent", # Removed - Missing fetch_volume_series
        ],
        CategoryType.SENTIMENT: [
            "news_sentiment_agent",
            "social_sentiment_agent",
            # "nlp_topic_agent", # Removed - Missing file
        ],
        CategoryType.RISK: [
            "beta_agent",
            "var_agent",
            # "risk_core_agent", # Removed - Missing file (base.py)
            # "portfolio_risk_agent", # Removed - Missing file
        ],
        CategoryType.MACRO: [
            # "interest_rate_agent", # Removed - Missing fetch_interest_rate
            # "inflation_agent", # Removed - Missing fetch_inflation_rate
            # "gdp_growth_agent", # Removed - Missing fetch_gdp_growth
        ],
        CategoryType.EVENT: [
            # "earnings_agent", # Removed - Missing file
            "corporate_actions_agent",
            "share_buyback_agent",
        ],
        CategoryType.ESG: [
            "environmental_agent",
            "social_agent",
            "governance_agent",
            # "composite_esg_agent", # Removed - Cache import issue
        ],
        CategoryType.INTELLIGENCE: [
            "composite_valuation_agent",
            "target_price_agent",
            "theme_match_agent",
            "peer_compare_agent",
            # "factor_score_agent", # Removed - Missing file (base.py)
            # "ask_alpha_agent", # Removed - Missing file
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
        cls, category: CategoryType, symbol: str, context: Dict = None # Context parameter is kept for signature compatibility but ignored
    ) -> List[Dict]:
        """Execute all agents in a category, ensuring each agent starts with a clean context."""
        agents = await cls.get_category_agents(category)
        results = []
        for agent_func in agents: # Renamed variable for clarity
            agent_name = agent_func.__name__ if hasattr(agent_func, '__name__') else 'unknown_agent'
            try:
                # Pass an empty dictionary to each agent, ignoring the passed context
                # Assuming agent signature is async def run(symbol) or handled by decorator
                result = await agent_func(symbol) # Remove agent_outputs={}
                if result:
                    # Ensure agent_name is included if not already present
                    if 'agent_name' not in result: # Add missing colon
                        result['agent_name'] = agent_name
                    results.append(result)
            except ValueError as e:
                logger.error(f"Agent {agent_name} failed for {symbol} with ValueError: {e}")
                results.append({
                    'agent_name': agent_name,
                    'symbol': symbol,
                    'status': 'error',
                    'error': f"ValueError: {e}",
                    'details': {}
                })
            except Exception as e:
                logger.error(f"Agent {agent_name} failed for {symbol} with unexpected error: {e}", exc_info=True) # Added traceback
                results.append({
                    'agent_name': agent_name,
                    'symbol': symbol,
                    'status': 'error',
                    'error': f"Unexpected error: {e}",
                    'details': {}
                })
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
    def get_dependencies(cls, category: CategoryType) -> List[str]: # Return uppercase names
        """Get the list of dependency category names (uppercase strings)."""
        metadata = cls.CATEGORY_METADATA.get(category)
        if metadata and metadata.dependencies:
            # Directly return the names stored in metadata
            return metadata.dependencies
        return []

    @classmethod
    def get_registered_agents(cls, category: CategoryType) -> List[str]:
        """Retrieve registered agents for a given category."""
        return cls._agent_registry.get(category, [])

    @classmethod
    def get_category_weights(cls) -> Dict[str, float]:
        """Get a dictionary mapping category values to their weights."""
        return {cat.value: meta.weight for cat, meta in cls.CATEGORY_METADATA.items()}
