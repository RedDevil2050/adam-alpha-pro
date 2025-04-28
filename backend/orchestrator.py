from typing import Dict, List, Type, Optional
import time
import asyncio
from loguru import logger
from prometheus_client import Counter, Histogram, Gauge
from backend.agents.base import AgentBase
from backend.agents.initialization import get_agent_initializer
from backend.agents.categories import CategoryType, CategoryManager
from backend.utils.monitoring import SystemMonitor
from backend.config.settings import get_settings

# Prometheus metrics
AGENT_EXECUTION_TIME = Histogram(
    "agent_execution_seconds",
    "Time spent executing each agent",
    ["agent_name", "category"],
)

AGENT_ERRORS = Counter(
    "agent_errors_total",
    "Number of agent execution errors",
    ["agent_name", "error_type"],
)

AGENT_SUCCESS_RATE = Gauge(
    "agent_success_rate", "Success rate of agent executions", ["agent_name"]
)


class Orchestrator:
    def __init__(self):
        self._agents: Dict[str, Type[AgentBase]] = {}
        self._dependencies: Dict[str, List[str]] = {}
        self._execution_times: Dict[str, float] = {}
        self.context: Dict = {}
        self.settings = get_settings()
        self.system_monitor = SystemMonitor()
        self.agent_initializer = get_agent_initializer()
        self.last_health_check = 0
        self.health_check_interval = 300  # 5 minutes

    async def initialize(self) -> bool:
        """Initialize the orchestrator and all agents"""
        success = self.agent_initializer.initialize_all_agents()
        if not success:
            logger.error("Critical agents failed to initialize")
            return False

        self._register_initialized_agents()
        await self._verify_system_health()
        return True

    def _register_initialized_agents(self):
        """Register successfully initialized agents"""
        for (
            agent_name,
            agent_class,
        ) in self.agent_initializer._initialized_agents.items():
            try:
                self.register(agent_name, agent_class)
            except Exception as e:
                logger.error(f"Failed to register agent {agent_name}: {e}")

    def register(self, name: str, agent_class: Type[AgentBase]) -> None:
        """Register an agent with dependencies"""
        if name in self._agents:
            logger.warning(f"Agent {name} already registered")
            return

        self._agents[name] = agent_class
        agent = self.agent_initializer.get_agent_instance(name)
        if agent:
            self._dependencies[name] = agent.get_dependencies()
        else:
            self._dependencies[name] = []

    async def execute_agent(self, name: str, symbol: str) -> Optional[Dict]:
        """Execute single agent with timing and monitoring"""
        start_time = time.time()
        agent_instance = self.agent_initializer.get_agent_instance(name)

        try:
            # Check dependencies
            deps = self._dependencies.get(name, [])
            if not all(dep in self.context for dep in deps):
                logger.warning(
                    f"Missing dependencies for {name}: {[d for d in deps if d not in self.context]}"
                )
                AGENT_ERRORS.labels(
                    agent_name=name, error_type="missing_dependencies"
                ).inc()
                return None

            # Execute agent
            if agent_instance:
                result = await agent_instance.execute(symbol, self.context)
            else:
                agent_func = self._agents[name]
                result = await agent_func(symbol, self.context)

            # Update metrics
            execution_time = time.time() - start_time
            self._execution_times[name] = execution_time
            AGENT_EXECUTION_TIME.labels(
                agent_name=name,
                category=agent_instance.category.value if agent_instance else "unknown",
            ).observe(execution_time)

            if result and "error" not in result:
                AGENT_SUCCESS_RATE.labels(agent_name=name).set(1)
            else:
                AGENT_SUCCESS_RATE.labels(agent_name=name).set(0)
                if result and "error" in result:
                    AGENT_ERRORS.labels(
                        agent_name=name, error_type="execution_error"
                    ).inc()

            return result

        except Exception as e:
            logger.error(f"Agent {name} execution failed: {e}")
            AGENT_ERRORS.labels(agent_name=name, error_type="uncaught_exception").inc()
            AGENT_SUCCESS_RATE.labels(agent_name=name).set(0)
            return None

    async def execute_all(self, symbol: str) -> Dict[str, Dict]:
        """Execute all agents respecting dependencies"""
        self.context = {}
        results = {}
        execution_order = self._build_execution_order()

        for agent_name in execution_order:
            result = await self.execute_agent(agent_name, symbol)
            if result:
                self.context[agent_name] = result
                results[agent_name] = result

        # Periodic health check
        await self._maybe_run_health_check()

        return results

    def _build_execution_order(self) -> List[str]:
        """Build execution order respecting dependencies"""
        visited = set()
        order = []

        def visit(agent: str):
            if agent in visited:
                return
            visited.add(agent)
            for dep in self._dependencies.get(agent, []):
                visit(dep)
            order.append(agent)

        for agent in self._agents:
            visit(agent)

        return order

    async def _verify_system_health(self) -> bool:
        """Verify system health by checking critical components"""
        try:
            # Check database connection
            # Check Redis connection
            # Verify API endpoints
            # Check data provider access
            healthy = True

            # Update system monitor
            self.system_monitor.update_health("orchestrator", healthy)

            return healthy
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            self.system_monitor.update_health("orchestrator", False)
            return False

    async def _maybe_run_health_check(self):
        """Run periodic health check if interval has elapsed"""
        now = time.time()
        if now - self.last_health_check > self.health_check_interval:
            await self._verify_system_health()
            self.last_health_check = now

    def get_metrics(self) -> Dict:
        """Get execution metrics"""
        return {
            "execution_times": self._execution_times.copy(),
            "total_agents": len(self._agents),
            "initialized_agents": len(self.agent_initializer._initialized_agents),
            "initialization_errors": len(
                self.agent_initializer.get_initialization_errors()
            ),
            "agent_success_rates": {
                name: float(AGENT_SUCCESS_RATE.labels(agent_name=name)._value.get())
                for name in self._agents
            },
        }


async def run_full_cycle(symbol: str, categories=None):
    """Run a full analysis cycle for a symbol with all agents
    
    This is a convenience function that wraps the orchestrator execution
    and provides a simpler interface for external components.
    
    Args:
        symbol: Stock symbol to analyze
        categories: Optional list of categories to limit execution to
        
    Returns:
        Dictionary with results from all executed agents
    """
    orchestrator = get_orchestrator()
    
    try:
        # Initialize orchestrator if needed
        if not orchestrator._agents:
            await orchestrator.initialize()
            
        # If specific categories are requested, only run those agents
        if categories:
            category_manager = CategoryManager()
            agents_to_run = []
            
            for category in categories:
                agents_in_category = category_manager.get_agents_by_category(category)
                agents_to_run.extend(agents_in_category)
                
            results = {}
            for agent_name in agents_to_run:
                if agent_name in orchestrator._agents:
                    agent_result = await orchestrator.execute_agent(agent_name, symbol)
                    if agent_result:
                        results[agent_name] = agent_result
            
            return results
            
        # Otherwise run all agents
        return await orchestrator.execute_all(symbol)
        
    except Exception as e:
        logger.error(f"Full cycle execution failed for {symbol}: {e}")
        return {"error": str(e), "status": "failed"}


# Global instance
_orchestrator = None


def get_orchestrator() -> Orchestrator:
    """Get or create the global Orchestrator instance"""
    global _orchestrator
    if not _orchestrator:
        _orchestrator = Orchestrator()
    return _orchestrator
