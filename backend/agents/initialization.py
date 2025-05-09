import importlib
import pkgutil
import inspect
from typing import Dict, Any, List, Optional, Type
from loguru import logger

# Attempt to import AgentBase. If it's in a different location or named differently (e.g., BaseAgent),
# this import will need to be adjusted.
# For now, assuming it's available as backend.agents.base.AgentBase
try:
    from backend.agents.base import AgentBase
except ImportError:
    logger.warning("Could not import AgentBase from backend.agents.base. Falling back to checking for 'execute' method for class agents.")
    # Define a dummy AgentBase if not found, so isinstance checks don't break,
    # but rely on hasattr for 'execute'
    class AgentBase: pass


class AgentInitializer:
    def __init__(self):
        # Stores successfully initialized agents: {agent_name: instance_or_function}
        self._initialized_agents: Dict[str, Any] = {}
        # Stores initialization errors: {agent_name: error_message}
        self._initialization_errors: Dict[str, str] = {}
        self._is_initialized = False

    def initialize_all_agents(self) -> bool:
        """
        Discovers and initializes all agents in the backend.agents package.
        Returns True if initialization process completed (doesn't guarantee all agents succeeded).
        """
        if self._is_initialized:
            logger.info("AgentInitializer already initialized.")
            # Return based on previous success or re-evaluate if needed.
            # For now, assume if initialized once, it's done.
            return len(self._initialized_agents) > 0 or not self._initialization_errors

        logger.info("Starting agent initialization...")
        self._initialized_agents.clear()
        self._initialization_errors.clear()

        agents_package_path = "backend.agents"
        try:
            agents_package = importlib.import_module(agents_package_path)
        except ImportError:
            logger.error(f"Could not import the main agents package: {agents_package_path}")
            self._is_initialized = True # Mark as initialized to prevent re-attempts
            return False

        for _, module_name_suffix, ispkg in pkgutil.walk_packages(
            path=agents_package.__path__, prefix=agents_package.__name__ + "."
        ):
            if ispkg:
                # logger.debug(f"Skipping package: {module_name_suffix}")
                continue # Skip packages, only process modules

            # Skip __init__.py files explicitly if they are not meant to be agents
            if module_name_suffix.endswith(".__init__"):
                # logger.debug(f"Skipping __init__ module: {module_name_suffix}")
                continue

            try:
                module = importlib.import_module(module_name_suffix)
                agent_name_from_module: Optional[str] = None
                agent_callable_or_instance: Optional[Any] = None

                # Strategy 1: Look for a module-level 'agent_name' variable and 'run' function (functional agents)
                if hasattr(module, "agent_name") and isinstance(module.agent_name, str) and \
                   hasattr(module, "run") and inspect.iscoroutinefunction(module.run):
                    agent_name_from_module = module.agent_name
                    agent_callable_or_instance = module.run # Store the run function directly
                    logger.debug(f"Found functional agent: {agent_name_from_module} in module {module_name_suffix}")

                # Strategy 2: Look for a class that might be an agent
                # This strategy is more complex due to various class naming conventions.
                # We'll iterate through classes defined in the module.
                else:
                    for attr_name in dir(module):
                        if attr_name.startswith("_"): # Skip private/magic attributes
                            continue
                        
                        potential_class = getattr(module, attr_name)
                        if inspect.isclass(potential_class) and potential_class.__module__ == module_name_suffix:
                            # Check if class has 'agent_name' attribute and an 'execute' method
                            class_agent_name = getattr(potential_class, 'agent_name', None)
                            if class_agent_name is None and hasattr(module, 'agent_name') and isinstance(module.agent_name, str):
                                # Fallback: if class is named same as module's agent_name
                                if potential_class.__name__.lower() == module.agent_name.replace("_agent","").lower() or potential_class.__name__ == module.agent_name:
                                     class_agent_name = module.agent_name

                            if isinstance(class_agent_name, str) and \
                               hasattr(potential_class, 'execute') and \
                               inspect.iscoroutinefunction(potential_class.execute):
                                
                                # Check if it's a subclass of AgentBase (if AgentBase was imported)
                                # or just has the execute method.
                                if AgentBase.__name__ != "AgentBase" or isinstance(potential_class, type) and issubclass(potential_class, AgentBase):
                                    pass # It's an AgentBase subclass
                                elif not (AgentBase.__name__ != "AgentBase" or isinstance(potential_class, type) and issubclass(potential_class, AgentBase)) and hasattr(potential_class, 'execute'):
                                    logger.debug(f"Class {potential_class.__name__} in {module_name_suffix} has 'execute' but is not AgentBase subclass. Proceeding.")
                                    pass
                                else: # Does not meet class criteria
                                    continue

                                agent_name_from_module = class_agent_name
                                try:
                                    agent_callable_or_instance = potential_class() # Instantiate the class
                                    logger.debug(f"Instantiated class-based agent: {agent_name_from_module} from class {potential_class.__name__} in module {module_name_suffix}")
                                    break # Found and instantiated a class agent in this module
                                except Exception as inst_e:
                                    logger.error(f"Failed to instantiate agent class {potential_class.__name__} (intended name: {agent_name_from_module}) in module {module_name_suffix}: {inst_e}")
                                    self._initialization_errors[agent_name_from_module or f"{module_name_suffix}.{potential_class.__name__}"] = f"Instantiation failed: {inst_e}"
                                    agent_name_from_module = None # Reset if instantiation failed
                                    agent_callable_or_instance = None
                                    continue # Try next class in module

                if agent_name_from_module and agent_callable_or_instance:
                    if agent_name_from_module in self._initialized_agents:
                        registered_origin_module = "unknown source"
                        registered_agent = self._initialized_agents[agent_name_from_module]
                        if hasattr(registered_agent, '__module__'):
                            registered_origin_module = registered_agent.__module__
                        elif inspect.isclass(registered_agent): # It's a class type
                            registered_origin_module = registered_agent.__module__

                        logger.warning(
                            f"Duplicate agent name found: {agent_name_from_module} in module {module_name_suffix}. "
                            f"Already registered from {registered_origin_module}. Skipping."
                        )
                        self._initialization_errors[agent_name_from_module] = f"Duplicate agent name (original: {registered_origin_module})"
                    else:
                        self._initialized_agents[agent_name_from_module] = agent_callable_or_instance
                        logger.info(f"Initialized agent: {agent_name_from_module} from module {module_name_suffix}")
                elif not module_name_suffix.endswith(('.base', '.utils', '.decorators', '.initialization', '.categories', '.registry', '.base_agent')): # Avoid logging utility modules
                    logger.debug(f"Module {module_name_suffix} did not yield a recognized agent format.")

            except ImportError as ie:
                logger.error(f"Could not import module {module_name_suffix}: {ie}")
                self._initialization_errors[module_name_suffix] = f"ImportError: {ie}"
            except Exception as e:
                logger.error(f"Error processing module {module_name_suffix} for agents: {e}", exc_info=True)
                self._initialization_errors[module_name_suffix] = f"General processing error: {e}"

        self._is_initialized = True
        logger.info(f"Agent initialization finished. Successfully initialized {len(self._initialized_agents)} agents. Encountered {len(self._initialization_errors)} errors during discovery/initialization.")
        if self._initialization_errors:
            logger.warning(f"Initialization errors: {self._initialization_errors}")

        return True # Returns true if process completed, check errors for specifics

    def get_agent_instance(self, name: str) -> Any:
        """Retrieves an initialized agent instance or function by name."""
        if not self._is_initialized:
            # This case should ideally be handled by calling initialize_all_agents first.
            # For robustness, we can try to initialize if not done.
            logger.warning("AgentInitializer.get_agent_instance called before explicit initialization. Attempting to initialize now.")
            self.initialize_all_agents()

        agent = self._initialized_agents.get(name)
        if agent is None:
            logger.debug(f"Agent '{name}' not found in initialized agents. Available: {list(self._initialized_agents.keys())}")
        return agent

    def get_initialization_errors(self) -> Dict[str, str]:
        """Returns a dictionary of agents/modules that failed to initialize and their errors."""
        return self._initialization_errors.copy()

    def get_initialized_agent_names(self) -> List[str]:
        """Returns a list of names of successfully initialized agents."""
        return list(self._initialized_agents.keys())

# Global instance
_agent_initializer_instance: Optional[AgentInitializer] = None

def get_agent_initializer() -> AgentInitializer:
    """Get or create the global AgentInitializer instance."""
    global _agent_initializer_instance
    if _agent_initializer_instance is None:
        _agent_initializer_instance = AgentInitializer()
    return _agent_initializer_instance