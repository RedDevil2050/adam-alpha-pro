from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, TypeVar
import logging
from datetime import datetime, timezone
from backend.utils.cache_utils import get_redis_client
from backend.config.settings import settings, AgentSettings # Added AgentSettings
from backend.agents.categories import CategoryType, CategoryManager
import json
from pydantic import ValidationError # Added ValidationError
from backend.models.common_models import VerdictType, MarketRegime # Added VerdictType, MarketRegime
from backend.data.providers.base_provider import BaseDataProvider # Added BaseDataProvider

T = TypeVar('T', bound='AgentBase')

class AgentBase(ABC):
    version: str = "1.0.0"
    agent_type: str = "base"
    description: str = "A base agent."
    
    name: str
    settings: AgentSettings 
    logger: Any # BaseLogger
    cache_client: Any # BaseCacheClient
    data_provider: BaseDataProvider
    market_context_provider: Any # BaseMarketContextProvider

    def __init__(self, 
                 name: str, 
                 settings: AgentSettings, 
                 logger: Any, # BaseLogger
                 cache_client: Any, # BaseCacheClient
                 data_provider: BaseDataProvider,
                 market_context_provider: Any, # BaseMarketContextProvider
                 **kwargs): # Allow for additional subclass-specific args
        self.name = name
        self.settings = settings
        self.logger = logger
        self.cache_client = cache_client
        self.data_provider = data_provider
        self.market_context_provider = market_context_provider
        # self._last_execution_time = None # Not currently used
        # self._last_verdict = None # Not currently used
        self.logger.debug(f"Agent {self.name} v{self.version} initialized.")

    def _generate_cache_key(self, symbol: str, agent_outputs: Dict[str, Any], **kwargs) -> str:
        """Generate a cache key for storing/retrieving agent results."""
        key_components = [self.agent_type, symbol, json.dumps(agent_outputs, sort_keys=True)]
        if kwargs:
            key_components.append(json.dumps(kwargs, sort_keys=True))
        return ":".join(key_components)

    async def _get_from_cache(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve data from cache."""
        try:
            cached_data = await self.cache_client.get(key) # Changed self.cache to self.cache_client
            if cached_data:
                return json.loads(cached_data)
        except Exception as e:
            self.logger.warning(f"Cache get error for {key}: {e}")
        return None

    async def _set_to_cache(self, key:str, value: Dict[str, Any], ttl: Optional[int] = None):
        """Store data in cache with optional TTL."""
        try:
            await self.cache_client.set(key, json.dumps(value), ex=ttl or self.settings.agent_cache_ttl) # Changed self.cache to self.cache_client and self.ttl to self.settings.agent_cache_ttl
        except Exception as e:
            self.logger.warning(f"Cache set error for {key}: {e}")

    async def execute(self, symbol:str, agent_outputs: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        self.logger.info(f"Executing agent {self.name} for symbol {symbol} with params: {kwargs}")
        
        cache_key = self._generate_cache_key(symbol, agent_outputs, **kwargs)
        
        # Ensure settings is available and has agent_cache_enabled attribute
        if hasattr(self.settings, 'agent_cache_enabled') and self.settings.agent_cache_enabled:
            cached_result = await self._get_from_cache(cache_key)
            if cached_result:
                # Update timestamp and mark as cached
                return self._format_output(
                    verdict=cached_result.get("verdict"),
                    confidence=cached_result.get("confidence"),
                    symbol=cached_result.get("symbol", symbol), # Use cached symbol or current
                    details=cached_result.get("details"),
                    data=cached_result.get("data"),
                    retrieved_from_cache=True
                )

        try:
            # The core logic of the agent
            raw_result = await self._execute(symbol, agent_outputs, **kwargs)
            
            if not isinstance(raw_result, dict) or not all(k in raw_result for k in ["verdict", "confidence", "details"]):
                self.logger.error(f"Agent {self.name}._execute for {symbol} did not return a dict with required keys (verdict, confidence, details). Result: {raw_result}")
                return self._error_response(
                    "Internal error: _execute response malformed or incomplete.",
                    details={"malformed_raw_result": True, "raw_result_preview": str(raw_result)[:200]}
                )

            final_result = self._format_output(
                verdict=raw_result["verdict"],
                confidence=raw_result["confidence"],
                symbol=symbol, 
                details=raw_result["details"],
                data=raw_result.get("data") 
            )

            # Ensure settings is available and has agent_cache_enabled attribute
            if hasattr(self.settings, 'agent_cache_enabled') and self.settings.agent_cache_enabled:
                await self._set_to_cache(cache_key, final_result)
            
            return final_result

        except ValidationError as ve:
            self.logger.error(f"Validation error in agent {self.name} for {symbol}: {ve}")
            return self._error_response(
                "Input validation error.", 
                details={"errors": ve.errors()}
            )
        except Exception as e:
            self.logger.error(f"Unhandled error in agent {self.name} execute for {symbol}: {e}", exc_info=True)
            return self._error_response(
                f"Unhandled agent error: {str(e)}",
                details={"exception_type": type(e).__name__, "exception_message": str(e)}
            )

    @abstractmethod
    async def _execute(self, symbol: str, agent_outputs: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Core agent logic. Expected to return a dictionary containing at least:
        - 'verdict': The agent's decision (e.g., VerdictType.BUY, "HOLD_NEUTRAL")
        - 'confidence': The confidence in this verdict (0.0 to 1.0)
        - 'details': A dictionary with specific data points supporting the verdict (e.g., k, d values for stochastic)
        It can optionally return a 'data' field for other structured information.
        """
        pass

    def _error_response(self, 
                        error_message: str, 
                        error_code: Optional[str] = None, 
                        status_code: int = 500,
                        details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self.logger.error(f"Agent {self.name} encountered an error: {error_message}{f' Details: {details}' if details else ''}")
        
        base_details = {
            "error_message": error_message,
            "error_code": error_code,
            "status_code": status_code
        }
        if details:
            base_details.update(details) # Merge provided details

        response = {
            "verdict": VerdictType.ERROR.value,
            "confidence": 0.0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent_name": self.name,
            "agent_version": self.version,
            "details": base_details        }
        return response
        
    def _format_output(self, 
                       verdict: Any, # Can be VerdictType enum or string value
                       confidence: float, 
                       symbol: str, 
                       details: Dict[str, Any], 
                       data: Optional[Dict[str, Any]] = None,
                       retrieved_from_cache: bool = False) -> Dict[str, Any]:
        output = {
            "verdict": verdict.value if isinstance(verdict, VerdictType) else str(verdict),
            "confidence": confidence,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent_name": self.name,
            "agent_version": self.version,
            "symbol": symbol,
            "details": details if details is not None else {},
            "retrieved_from_cache": retrieved_from_cache
        }
        if data:
            output["data"] = data # Optional field for any other structured data
            
        # Include 'value' field if it exists in details (for backward compatibility with tests)
        if details and "value" in details:
            output["value"] = details["value"]
        
        # Ensure confidence is within bounds
        output["confidence"] = max(0.0, min(1.0, output["confidence"]))
        return output

    async def get_market_context(self, symbol: str, default_regime: MarketRegime = MarketRegime.NEUTRAL) -> Dict[str, Any]:
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

    async def initialize(self):
        """Initialize agent resources (e.g., cache). Override in subclasses if needed."""
        if self.cache is None:
            self.cache = await get_redis_client()
