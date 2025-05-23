import logging
from datetime import datetime
from typing import Dict, Optional, Any
import psutil

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SystemMonitor:
    def __init__(self):
        self._analyses = {}
        self.components = {}
        self.start_time = datetime.now()
        self._initialize_metrics()

    def register_component(self, name: str):
        """Register a new component with the monitor."""
        if name not in self.components:
            self.components[name] = {"status": "initializing", "last_updated": datetime.now()}
            self.metrics["component_status"][name] = "initializing"
            # Optionally log component registration
            # logger.info(f\"Component '{name}' registered.\")

    def update_component_status(self, name: str, status: str):
        """Update the status of a registered component."""
        if name in self.components:
            self.components[name]["status"] = status
            self.components[name]["last_updated"] = datetime.now()
            self.metrics['component_status'][name] = status
        else:
            # Optionally log or raise an error for unregistered components
            # logger.warning(f\"Attempted to update status for unregistered component '{name}'.\")
            pass # Or raise ValueError(f\"Component '{name}' not registered.\")
            
    def update_health(self, component_name: str, is_healthy: bool):
        """Update health status of a specific component.
        
        Args:
            component_name: Name of the component to update.
            is_healthy: Boolean indicating whether the component is healthy.
        """
        status = "healthy" if is_healthy else "unhealthy"
        logger.debug(f"SystemMonitor: Updating health for {component_name} to {status}")
        self.update_component_status(component_name, status)

    # Added missing method required by E2E tests/tracker
    async def update_agent_status(self, category: str, agent_name: str, symbol: str, status: str, details: Optional[Any] = None):
        """Placeholder/Mock for updating agent status (async to match potential real implementation)."""
        # In a real implementation, this would log or store the status update,
        # potentially interacting with a database or monitoring service.
        # Using logger.debug to avoid excessive console noise during tests.
        logger.debug(f"Tracker: Agent {category}/{agent_name} for {symbol} status updated to {status}. Details: {details}")
        # No actual state change needed for this placeholder
        pass

    # Make start_analysis async
    async def start_analysis(self, analysis_id: str):
        """Record the start time and initial state for an analysis."""
        logger.info(f"SystemMonitor: Starting analysis {analysis_id}")
        self._analyses[analysis_id] = {"start_time": datetime.now(), "status": "running"}

    # Correct indentation for the following methods
    # Make end_analysis async
    async def end_analysis(self, analysis_id: str, status: str):
        """Record the end time and final status for an analysis."""
        logger.info(f"SystemMonitor: Ending analysis {analysis_id} with status {status}")
        if analysis_id in self._analyses:
            self._analyses[analysis_id]["end_time"] = datetime.now()
            self._analyses[analysis_id]["status"] = status
        else:
            logger.warning(f"SystemMonitor Warning: end_analysis called for unknown id {analysis_id}")

    async def get_health_metrics(self) -> Dict:
        """Provide system health metrics including CPU and memory."""
        # logger.debug("SystemMonitor: Getting health metrics (SIMPLIFIED FOR DEBUG)")
        # Actual CPU and Memory Usage
        cpu_usage = psutil.cpu_percent(interval=None) # Non-blocking, gets overall CPU usage
        memory_info = psutil.virtual_memory()

        return {
            "system": {
                 "cpu_usage": cpu_usage,
                 "memory_usage": memory_info.percent, # Using percentage for consistency
                 "memory_rss_bytes": psutil.Process().memory_info().rss # Actual RSS memory for the current process
            },
            "components": self.components
        }

    def _initialize_metrics(self):
        self.metrics = {
            "cpu_samples": [],
            "memory_samples": [],
            "error_counts": {},
            "component_status": {},
        }

    def is_ready(self) -> Dict:
        return {
            "ready": all(
                comp["status"] == "healthy" for comp in self.components.values()
            ),
            "components": {
                name: comp["status"] for name, comp in self.components.items()
            },
        }

    def check_system_health(self) -> Dict:
        return {
            "status": "healthy",
            "cpu": psutil.cpu_percent(),
            "memory": psutil.virtual_memory().percent,
        }
