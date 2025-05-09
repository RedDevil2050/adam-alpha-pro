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
        # self._agents: Dict[str, Type[AgentBase]] = {} # Old: Stored class type
        self._known_agent_names: set[str] = set() # Names of agents initializer claims to know and can provide instances for
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
        """Initialize the orchestrator by initializing agents via AgentInitializer
        and then registering the successfully initialized ones with this orchestrator instance.
        """
        if self._known_agent_names: # Already initialized
            logger.info("Orchestrator already initialized with known agents.")
            return True

        success = self.agent_initializer.initialize_all_agents()
        if not success:
            logger.error("Critical agents failed to initialize")
            return False

        self._register_initialized_agents() # Populate based on what AgentInitializer successfully initialized
        await self._verify_system_health()

        if not self._known_agent_names:
            logger.warning("Orchestrator initialization complete, but no agents were successfully registered with the orchestrator.")
            # Depending on requirements, this could be a critical failure.
            # For now, we allow it to proceed.
        return True

    def _register_initialized_agents(self):
        """Register agents that were successfully initialized by AgentInitializer."""
        self._known_agent_names.clear()
        self._dependencies.clear()

        initialized_agent_names_from_initializer = self.agent_initializer.get_initialized_agent_names()

        if not initialized_agent_names_from_initializer:
            logger.warning("AgentInitializer reported no initialized agents. Orchestrator will have no agents to run.")
            return

        for agent_name in initialized_agent_names_from_initializer:
            agent_instance_or_func = self.agent_initializer.get_agent_instance(agent_name)
            if agent_instance_or_func:
                self._known_agent_names.add(agent_name) # Add to orchestrator's known list
                # Get dependencies. Functional agents might not have get_dependencies directly.
                if hasattr(agent_instance_or_func, 'get_dependencies') and callable(agent_instance_or_func.get_dependencies):
                    self._dependencies[agent_name] = agent_instance_or_func.get_dependencies()
                else:
                    self._dependencies[agent_name] = [] # Default to no dependencies
                    logger.debug(f"Agent {agent_name} does not have get_dependencies method or it's not callable. Assuming no dependencies.")
                logger.info(f"Orchestrator: Agent {agent_name} acknowledged as initialized and dependencies registered.")
            else:
                logger.error(
                    f"Orchestrator: Agent {agent_name} listed as initialized by AgentInitializer, "
                    f"but get_agent_instance() returned None. It will not be available."
                )

    # The explicit `register` method is removed to enforce AgentInitializer as the sole source of agent list.
    # If dynamic registration is needed later, it should be added back with careful consideration.

    async def execute_agent(self, name: str, symbol: str) -> Optional[Dict]:
        """Execute single agent with timing and monitoring"""
        start_time = time.time()

        # Check against the orchestrator's own list of known agents,
        # which was populated from the initializer.
        if name not in self._known_agent_names:
            logger.error(
                f"Agent {name} is not in the orchestrator's list of known_agent_names. "
                f"It was either not initialized by AgentInitializer or failed registration here."
            )
            AGENT_ERRORS.labels(agent_name=name, error_type="unknown_agent").inc()
            # AGENT_SUCCESS_RATE.labels(agent_name=name).set(0) # Consider if to set for unknown
            return {"error": f"Agent {name} is unknown or not initialized", "agent_name": name}

        agent_instance = self.agent_initializer.get_agent_instance(name)

        if not agent_instance:
            logger.error(f"Agent {name} instance not found. Initialization might have failed.")
            # This path should ideally not be hit if `name` is in `_known_agent_names`
            # because `_known_agent_names` is populated based on successful `get_agent_instance` calls.
            # Logging it as a more severe "instance_not_found_inconsistency".
            AGENT_ERRORS.labels(agent_name=name, error_type="instance_not_found").inc()
            AGENT_SUCCESS_RATE.labels(agent_name=name).set(0)
            return {"error": f"Agent {name} instance not found (inconsistency)", "agent_name": name}

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

            # Execute agent instance or function
            if hasattr(agent_instance, 'execute') and callable(agent_instance.execute):
                # Class-based agent (e.g., AgentBase subclass)
                result = await agent_instance.execute(symbol, agent_outputs=self.context)
            elif callable(agent_instance):
                # Functional agent (e.g., a module-level 'run' function)
                # Inspect signature to pass agent_outputs if accepted
                import inspect
                sig = inspect.signature(agent_instance)
                if 'agent_outputs' in sig.parameters:
                    result = await agent_instance(symbol, agent_outputs=self.context)
                else:
                    result = await agent_instance(symbol)
            else:
                logger.error(f"Agent {name} is neither a callable nor has a callable 'execute' method.")
                AGENT_ERRORS.labels(agent_name=name, error_type="not_executable").inc()
                AGENT_SUCCESS_RATE.labels(agent_name=name).set(0)
                return {"error": f"Agent {name} not executable", "agent_name": name}

            # Update metrics
            execution_time = time.time() - start_time
            self._execution_times[name] = execution_time
            
            category_value = "unknown" # Default category
            if hasattr(agent_instance, 'category') and agent_instance.category:
                category_value = agent_instance.category.value
            else:
                logger.warning(f"Agent {name} instance is missing 'category' attribute or it's None.")

            AGENT_EXECUTION_TIME.labels(
                agent_name=name,
                category=category_value,
            ).observe(execution_time) # type: ignore

            # Validate result structure slightly more robustly
            if result and isinstance(result, dict) and result.get("error") is None:
                AGENT_SUCCESS_RATE.labels(agent_name=name).set(1)
            else:
                AGENT_SUCCESS_RATE.labels(agent_name=name).set(0)
                error_type = "execution_error"
                error_reason = "Unknown execution error" # Default
                if result and isinstance(result, dict) and result.get("error"):
                    error_reason = result['error']
                    logger.warning(f"Agent {name} returned error: {error_reason}")
                else:
                    error_reason = f"Agent returned invalid/null result: {result}"
                    logger.warning(error_reason)
                    error_type = "invalid_result"

                AGENT_ERRORS.labels(
                    agent_name=name, error_type=error_type
                ).inc()
                # Ensure a consistent error structure is returned if agent didn't provide one
                if not result or not isinstance(result, dict) or "agent_name" not in result: # Check for agent_name
                     result = {
                        "symbol": symbol,
                        "verdict": "ERROR",
                        "confidence": 0.0,
                        "value": None,
                        "details": {"reason": error_reason},
                        "error": error_reason,
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
            # This check is now redundant because _build_execution_order iterates _known_agent_names
            # if agent_name not in self._known_agent_names:
            #     logger.warning(f"Agent {agent_name} in execution order but not in known_agent_names. This shouldn't happen. Skipping.")
            #     continue

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
                # Only visit dependencies that are known and initialized
                if dep in self._known_agent_names:
                    visit(dep)
                else:
                    logger.warning(
                        f"Dependency '{dep}' for agent '{agent}' is not in _known_agent_names. "
                        f"It might have failed initialization. Skipping this dependency in execution order."
                    )
            # Append after visiting all dependencies
            order.append(agent)

        # Iterate over a sorted list of known agent names for deterministic order if dependencies are similar
        # Iterate over orchestrator's known agents
        for agent in sorted(list(self._known_agent_names)):
            visit(agent)

        logger.debug(f"Built execution order: {order}")
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
            "total_known_agents": len(self._known_agent_names),
            "initialized_agents_by_initializer": len(self.agent_initializer.get_initialized_agent_names()),
            "initialization_errors_by_initializer": len(
                self.agent_initializer.get_initialization_errors()
            ),
            "agent_success_rates": {
                # Iterate over orchestrator's known agents for success rate reporting
                name: AGENT_SUCCESS_RATE.labels(agent_name=name)._value.get() # type: ignore
                for name in self._known_agent_names
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
        # Initialize orchestrator if it hasn't been already (e.g. no known agents)
        if not orchestrator._known_agent_names:
            initialized = await orchestrator.initialize()
            if not initialized or not orchestrator._known_agent_names: # Check again after initialization
                 logger.error("Orchestrator failed to initialize or no agents were registered.")
                 return {"error": "Orchestrator failed to initialize", "status": "failed"}

        # If specific categories are requested, filter agents
        if categories:
            category_manager = CategoryManager() # Assuming this exists and works
            agents_to_run_names = set() # Use a set to avoid duplicates

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
                 # CategoryManager.get_registered_agents returns agent names for that category
                 agents_in_cat = category_manager.get_registered_agents(category_enum)
                 agents_to_run_names.update(agents_in_cat) # Add agent names to the set


            if not agents_to_run_names:
                 return {"error": f"No agents found for specified categories: {categories}", "status": "failed"}

            results = {}
            orchestrator.context = {}
            full_order = orchestrator._build_execution_order()
            # Filter the full order to only include agents we want to run for these categories
            # AND are known to the orchestrator
            ordered_subset_to_run = [
                agent_name for agent_name in full_order
                # Crucially, check against orchestrator's _known_agent_names
                if agent_name in agents_to_run_names and agent_name in orchestrator._known_agent_names
            ]
            
            missing_from_known = agents_to_run_names - set(ordered_subset_to_run)
            if missing_from_known:
                logger.warning(f"Agents {missing_from_known} were requested by category but are not registered or initialized with the orchestrator.")

            if not ordered_subset_to_run:
                logger.warning(f"No agents to run for categories {categories} after filtering against known agents.")
                return {"error": f"No executable agents found for specified categories: {categories}", "status": "failed"}

            for agent_name in ordered_subset_to_run:
                 # This check is now implicitly handled by how ordered_subset_to_run is constructed
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
