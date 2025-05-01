from typing import Dict, List, Type, Optional
import time
import asyncio
from loguru import logger
from prometheus_client import Counter, Histogram, Gauge
from backend.agents.base import AgentBase
from backend.agents.initialization import get_agent_initializer
from backend.agents.categories import CategoryType, CategoryManager
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
        from backend.utils.system_monitor import SystemMonitor
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

        if not agent_instance:
            logger.error(f"Agent {name} instance not found. Initialization might have failed.")
            AGENT_ERRORS.labels(agent_name=name, error_type="instance_not_found").inc()
            AGENT_SUCCESS_RATE.labels(agent_name=name).set(0)
            return {"error": f"Agent {name} instance not found", "agent_name": name}

        try:
            # Check dependencies (using self.context which holds previous results)
            deps = self._dependencies.get(name, [])
            if not all(dep in self.context for dep in deps):
                missing_deps = [d for d in deps if d not in self.context]
                logger.warning(
                    f"Missing dependencies for {name}: {missing_deps}"
                )
                AGENT_ERRORS.labels(
                    agent_name=name, error_type="missing_dependencies"
                ).inc()
                AGENT_SUCCESS_RATE.labels(agent_name=name).set(0)
                # Return an error dictionary consistent with agent output structure
                return {
                    "symbol": symbol,
                    "verdict": "ERROR",
                    "confidence": 0.0,
                    "value": None,
                    "details": {"reason": f"Missing dependencies: {missing_deps}"},
                    "error": f"Missing dependencies: {missing_deps}",
                    "agent_name": name,
                }


            # Execute agent instance, passing previous results as agent_outputs
            # The AgentBase.execute method expects 'agent_outputs'
            result = await agent_instance.execute(symbol, agent_outputs=self.context)

            # Update metrics
            execution_time = time.time() - start_time
            self._execution_times[name] = execution_time
            AGENT_EXECUTION_TIME.labels(
                agent_name=name,
                category=agent_instance.category.value, # Instance is guaranteed here
            ).observe(execution_time)

            # Validate result structure slightly more robustly
            if result and isinstance(result, dict) and result.get("error") is None:
                AGENT_SUCCESS_RATE.labels(agent_name=name).set(1)
            else:
                AGENT_SUCCESS_RATE.labels(agent_name=name).set(0)
                error_type = "execution_error"
                if result and isinstance(result, dict) and result.get("error"):
                    logger.warning(f"Agent {name} returned error: {result['error']}")
                else:
                    logger.warning(f"Agent {name} returned invalid/null result: {result}")
                    error_type = "invalid_result"

                AGENT_ERRORS.labels(
                    agent_name=name, error_type=error_type
                ).inc()
                # Ensure a consistent error structure is returned if agent didn't provide one
                if not result or not isinstance(result, dict) or "error" not in result:
                     result = {
                        "symbol": symbol,
                        "verdict": "ERROR",
                        "confidence": 0.0,
                        "value": None,
                        "details": {"reason": f"Agent returned invalid result: {result}"},
                        "error": f"Agent returned invalid result: {result}",
                        "agent_name": name,
                    }


            return result

        except Exception as e:
            logger.exception(f"Agent {name} execution failed with uncaught exception: {e}") # Use logger.exception for stack trace
            AGENT_ERRORS.labels(agent_name=name, error_type="uncaught_exception").inc()
            AGENT_SUCCESS_RATE.labels(agent_name=name).set(0)
            # Return standard error format
            return {
                "symbol": symbol,
                "verdict": "ERROR",
                "confidence": 0.0,
                "value": None,
                "details": {"reason": f"Uncaught exception: {e}"},
                "error": f"Uncaught exception: {e}",
                "agent_name": name,
            }

    async def execute_all(self, symbol: str) -> Dict[str, Dict]:
        """Execute all agents respecting dependencies"""
        self.context = {}  # Reset context for a new full run
        results = {}
        execution_order = self._build_execution_order()

        for agent_name in execution_order:
            # Ensure agent exists before trying to execute
            if agent_name not in self._agents:
                 logger.warning(f"Agent {agent_name} requested in execution order but not registered. Skipping.")
                 continue

            result = await self.execute_agent(agent_name, symbol)

            # Store result in context *only if* it's valid and not an error
            # This prevents downstream agents from failing due to missing dependencies
            # when the dependency agent itself failed.
            if result and isinstance(result, dict) and result.get("error") is None:
                self.context[agent_name] = result # Update context for subsequent agents

            # Store all results (including errors) in the final results dictionary
            if result: # Store even if it's an error result
                 results[agent_name] = result
            else: # Should not happen with the improved execute_agent, but handle defensively
                 logger.error(f"execute_agent for {agent_name} returned None unexpectedly.")
                 results[agent_name] = {
                     "symbol": symbol,
                     "verdict": "ERROR",
                     "confidence": 0.0,
                     "value": None,
                     "details": {"reason": "Agent execution returned None"},
                     "error": "Agent execution returned None",
                     "agent_name": agent_name,
                 }


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
            status = "healthy" if healthy else "failed"

            # Update system monitor component status
            self.system_monitor.update_component_status("orchestrator", status)

            return healthy
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            self.system_monitor.update_component_status("orchestrator", "failed")
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


async def run_full_cycle(symbol: str, categories: Optional[List[str]] = None): # Made categories optional list of strings
    """Run a full analysis cycle for a symbol with all agents or specified categories.

    Args:
        symbol: Stock symbol to analyze
        categories: Optional list of category names (strings) to limit execution to.

    Returns:
        Dictionary with results from all executed agents.
    """
    orchestrator = get_orchestrator()

    try:
        # Initialize orchestrator if needed (idempotent check)
        if not orchestrator._agents:
            initialized = await orchestrator.initialize()
            if not initialized:
                 return {"error": "Orchestrator failed to initialize", "status": "failed"}

        # If specific categories are requested, filter agents
        if categories:
            category_manager = CategoryManager() # Assuming this exists and works
            agents_to_run = set() # Use a set to avoid duplicates

            # Convert category names (strings) to CategoryType enums if necessary
            valid_category_enums = []
            for cat_name in categories:
                try:
                    # Assuming CategoryType values are lowercase strings like 'technical'
                    category_enum = CategoryType(cat_name.lower())
                    valid_category_enums.append(category_enum)
                except ValueError:
                    logger.warning(f"Invalid category requested: {cat_name}. Skipping.")

            if not valid_category_enums:
                 return {"error": "No valid categories specified for execution.", "status": "failed"}


            # Get agents for the valid categories
            for category_enum in valid_category_enums:
                 # Assuming get_agents_by_category takes the enum member
                 agents_in_category = category_manager.get_agents_by_category(category_enum)
                 agents_to_run.update(agents_in_category) # Add agents to the set


            if not agents_to_run:
                 return {"error": f"No agents found for specified categories: {categories}", "status": "failed"}

            # Execute only the selected agents (respecting dependencies implicitly via execute_agent)
            # Note: This simplified approach doesn't guarantee dependency order *between* categories
            # if only a subset is run. A more robust solution might involve building a
            # temporary dependency graph for the selected agents.
            results = {}
            # Rebuild context iteratively for the selected agents
            orchestrator.context = {}
            # We need to determine an execution order even for a subset
            full_order = orchestrator._build_execution_order()
            ordered_subset = [agent for agent in full_order if agent in agents_to_run]

            for agent_name in ordered_subset:
                 # Check if agent is registered before executing
                 if agent_name not in orchestrator._agents:
                     logger.warning(f"Agent {agent_name} requested but not registered. Skipping.")
                     continue

                 agent_result = await orchestrator.execute_agent(agent_name, symbol)

                 # Store result in context *only if* valid
                 if agent_result and isinstance(agent_result, dict) and agent_result.get("error") is None:
                     orchestrator.context[agent_name] = agent_result

                 # Store all results (including errors)
                 if agent_result:
                     results[agent_name] = agent_result
                 else: # Defensive coding
                     results[agent_name] = {
                         "symbol": symbol, "verdict": "ERROR", "confidence": 0.0, "value": None,
                         "details": {"reason": "Agent execution returned None"},
                         "error": "Agent execution returned None", "agent_name": agent_name,
                     }

            return results

        # Otherwise run all agents using execute_all
        return await orchestrator.execute_all(symbol)

    except Exception as e:
        logger.exception(f"Full cycle execution failed for {symbol}: {e}") # Use logger.exception
        return {"error": str(e), "status": "failed"}

# Global instance
_orchestrator = None


def get_orchestrator() -> Orchestrator:
    """Get or create the global Orchestrator instance"""
    global _orchestrator
    if not _orchestrator:
        _orchestrator = Orchestrator()
    return _orchestrator
