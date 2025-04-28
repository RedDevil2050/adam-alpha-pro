import importlib
import os
from typing import Dict, List, Type, Optional
from loguru import logger
from backend.agents.base import AgentBase
from backend.agents.categories import CategoryType, CategoryManager
from backend.utils.metrics_collector import MetricsCollector
from backend.config.settings import get_settings

class AgentInitializer:
    """Handles agent initialization, validation, and dependency management"""
    
    def __init__(self):
        self.metrics = MetricsCollector()
        self.settings = get_settings()
        self._initialized_agents: Dict[str, Type[AgentBase]] = {}
        self._agent_instances: Dict[str, AgentBase] = {}
        self._initialization_errors: List[str] = []

    def initialize_all_agents(self) -> bool:
        """
        Initialize all registered agents and validate their implementations.
        Returns True if all critical agents are properly initialized.
        """
        success = True
        for category in CategoryType:
            try:
                agents = CategoryManager.get_registered_agents(category)
                for agent_name in agents:
                    if not self._initialize_agent(category, agent_name):
                        if self._is_critical_agent(category, agent_name):
                            success = False
            except Exception as e:
                logger.error(f"Failed to initialize category {category}: {e}")
                if self._is_critical_category(category):
                    success = False
        
        self._log_initialization_status()
        return success

    def _initialize_agent(self, category: CategoryType, agent_name: str) -> bool:
        """Initialize and validate a single agent"""
        try:
            # Import agent module
            module_path = f"backend.agents.{category.value}.{agent_name}"
            try:
                module = importlib.import_module(module_path)
            except ImportError as e:
                logger.error(f"Failed to import {module_path}: {e}")
                self._initialization_errors.append(f"Import error for {agent_name}: {e}")
                return False

            # Validate module structure
            if not hasattr(module, "run"):
                logger.error(f"Agent {agent_name} missing run function")
                self._initialization_errors.append(f"Missing run function in {agent_name}")
                return False

            # Get agent class if exists
            agent_class = None
            for attr in dir(module):
                obj = getattr(module, attr)
                if isinstance(obj, type) and issubclass(obj, AgentBase) and obj != AgentBase:
                    agent_class = obj
                    break

            # Initialize agent if class exists
            if agent_class:
                try:
                    instance = agent_class()
                    instance_name = f"{category.value}.{agent_name}"
                    self._agent_instances[instance_name] = instance
                    self._initialized_agents[agent_name] = agent_class
                    logger.info(f"Successfully initialized agent {agent_name}")
                    return True
                except Exception as e:
                    logger.error(f"Failed to instantiate {agent_name}: {e}")
                    self._initialization_errors.append(f"Instantiation error for {agent_name}: {e}")
                    return False
            else:
                # Function-based agent
                self._initialized_agents[agent_name] = module.run
                logger.info(f"Registered function-based agent {agent_name}")
                return True

        except Exception as e:
            logger.error(f"Unexpected error initializing {agent_name}: {e}")
            self._initialization_errors.append(f"Unexpected error in {agent_name}: {e}")
            return False

    def _is_critical_agent(self, category: CategoryType, agent_name: str) -> bool:
        """Determine if an agent is critical for system operation"""
        critical_agents = {
            CategoryType.VALUATION: ["pe_ratio_agent", "dcf_agent"],
            CategoryType.TECHNICAL: ["rsi_agent", "macd_agent"],
            CategoryType.MARKET: ["market_regime_agent"],
            CategoryType.RISK: ["risk_core_agent"],
            CategoryType.SENTIMENT: ["news_sentiment_agent"],
        }
        return agent_name in critical_agents.get(category, [])

    def _is_critical_category(self, category: CategoryType) -> bool:
        """Determine if a category is critical for system operation"""
        return category in {
            CategoryType.VALUATION,
            CategoryType.TECHNICAL,
            CategoryType.MARKET,
            CategoryType.RISK
        }

    def _log_initialization_status(self):
        """Log initialization status and metrics"""
        total_agents = len(self._initialized_agents)
        total_errors = len(self._initialization_errors)
        
        logger.info(f"Agent initialization complete: {total_agents} agents initialized")
        if total_errors > 0:
            logger.warning(f"{total_errors} initialization errors occurred")
            for error in self._initialization_errors:
                logger.warning(f"  - {error}")

        # Update metrics
        self.metrics.gauge("initialized_agents_total", total_agents)
        self.metrics.gauge("agent_initialization_errors", total_errors)

    def get_agent_instance(self, name: str) -> Optional[AgentBase]:
        """Get initialized agent instance by name"""
        return self._agent_instances.get(name)

    def get_initialization_errors(self) -> List[str]:
        """Get list of initialization errors"""
        return self._initialization_errors.copy()

    def validate_agent_implementation(self, agent_class: Type[AgentBase]) -> bool:
        """Validate agent class implementation"""
        required_methods = ["execute", "_execute" if hasattr(agent_class, "_execute") else "run"]
        
        for method in required_methods:
            if not hasattr(agent_class, method):
                logger.error(f"Agent {agent_class.__name__} missing required method: {method}")
                return False

        return True

# Global instance
_agent_initializer = None

def get_agent_initializer() -> AgentInitializer:
    """Get or create the global AgentInitializer instance"""
    global _agent_initializer
    if not _agent_initializer:
        _agent_initializer = AgentInitializer()
    return _agent_initializer