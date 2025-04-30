from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
import logging
from datetime import datetime
from backend.utils.cache_utils import get_redis_client
from backend.config.settings import settings
from backend.agents.categories import CategoryType, CategoryManager


class AgentBase(ABC):
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.cache = get_redis_client()
        self.ttl = settings.agent_cache_ttl
        self.context = {}
        self.metrics = {"calls": 0, "errors": 0, "avg_latency": 0}

    async def execute(self, symbol: str, agent_outputs: Dict = {}) -> Dict[str, Any]:
        """Template method for agent execution with metrics"""
        start_time = datetime.now()
        self.metrics["calls"] += 1

        try:
            cache_key = f"{self.__class__.__name__}:{symbol}"
            cached = await self.cache.get(cache_key)
            if cached:
                return cached

            result = await self._execute(symbol, agent_outputs)
            await self.cache.set(cache_key, result, ex=self.ttl)

            return result

        except Exception as e:
            self.metrics["errors"] += 1
            self.logger.error(f"Agent execution failed: {e}")
            return self._error_response(symbol, str(e))
        finally:
            latency = (datetime.now() - start_time).total_seconds()
            self._update_latency(latency)

    @abstractmethod
    async def _execute(self, symbol: str, agent_outputs: Dict) -> Dict[str, Any]:
        """Actual agent logic implementation"""
        pass

    def _error_response(self, symbol: str, error: str) -> Dict[str, Any]:
        return {
            "symbol": symbol,
            "verdict": "ERROR",
            "confidence": 0.0,
            "value": None,
            "details": {},
            "error": error,
            "agent_name": self.__class__.__name__,
        }

    def _update_latency(self, new_latency: float):
        old_avg = self.metrics["avg_latency"]
        calls = self.metrics["calls"]
        self.metrics["avg_latency"] = (old_avg * (calls - 1) + new_latency) / calls

    def get_dependencies(self) -> List[str]:
        """Return list of dependent agent names"""
        return []

    def get_weight(self) -> float:
        """Return agent weight for scoring"""
        return 1.0

    async def pre_execute(self, symbol: str, context: Dict) -> None:
        """Hook called before execution"""
        pass

    async def post_execute(self, result: Dict, context: Dict) -> None:
        """Hook called after execution"""
        pass

    def validate_result(self, result: Dict) -> bool:
        """Validate agent output"""
        required = ["symbol", "verdict", "confidence", "value"]
        return all(k in result for k in required)

    async def get_market_context(self, symbol: str) -> Dict[str, Any]:
        """Get current market context"""
        try:
            from backend.market.context import MarketContext

            ctx = await MarketContext.get_instance()
            return await ctx.get_state(symbol)
        except Exception as e:
            self.logger.error(f"Market context error: {e}")
            return {}

    def adjust_for_market_regime(self, score: float, regime: str) -> float:
        """Adjust score based on market regime"""
        regime_multipliers = {"BULL": 1.2, "BEAR": 0.8, "NEUTRAL": 1.0, "VOLATILE": 0.7}
        return score * regime_multipliers.get(regime, 1.0)

    async def get_execution_context(self, symbol: str) -> Dict[str, Any]:
        """Get execution context with market state"""
        market_state = await self.get_market_context(symbol)
        return {
            "timestamp": datetime.now().isoformat(),
            "market_regime": market_state.get("regime", "UNKNOWN"),
            "volatility": market_state.get("volatility", 0.0),
            "agent_name": self.__class__.__name__,
            "dependencies_met": self._check_dependencies(),
        }

    def _check_dependencies(self) -> bool:
        """Verify all dependencies are available"""
        deps = self.get_dependencies()
        return all(self._verify_dependency(d) for d in deps)

    def _verify_dependency(self, dep_name: str) -> bool:
        """Verify single dependency"""
        return dep_name in self.context.get("dependencies", {})

    @property
    def category(self) -> CategoryType:
        """Return agent category"""
        raise NotImplementedError

    def get_category_weight(self) -> float:
        """Get weight based on category"""
        return CategoryManager.get_category_weight(self.category)

    def get_category_dependencies(self) -> List[str]:
        """Get category-level dependencies"""
        return CategoryManager.get_dependencies(self.category)

    async def validate_category_requirements(self, context: Dict) -> bool:
        """Validate category-specific requirements"""
        deps = self.get_category_dependencies()
        return all(d in context for d in deps)

    async def validate_output(self, result: Dict, context: Dict) -> bool:
        """Validate agent output based on category"""
        if not self.validate_result(result):
            return False

        category_meta = CategoryManager.CATEGORY_METADATA.get(self.category)
        if not category_meta:
            return False

        # Check category-specific thresholds
        if category_meta.required and result["confidence"] < 0.5:
            return False

        # Validate dependencies
        if not await self.validate_category_requirements(context):
            return False

        return True

    def get_agent_priority(self) -> int:
        """Get execution priority based on category"""
        priorities = {
            CategoryType.MARKET: 1,
            CategoryType.TECHNICAL: 2,
            CategoryType.VALUATION: 3,
            CategoryType.RISK: 4,
            CategoryType.SENTIMENT: 5,
            CategoryType.EVENT: 6,
            CategoryType.ESG: 7,
            CategoryType.INTELLIGENCE: 8,
        }
        return priorities.get(self.category, 10)
