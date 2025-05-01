import logging
from datetime import datetime
from typing import Dict, Optional
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

    def start_analysis(self, analysis_id: str):
        """Record the start time and initial state for an analysis."""
        logger.info(f"SystemMonitor: Starting analysis {analysis_id}")
        self._analyses[analysis_id] = {"start_time": datetime.now(), "status": "running"}

    def end_analysis(self, analysis_id: str, status: str):
        """Record the end time and final status for an analysis."""
        logger.info(f"SystemMonitor: Ending analysis {analysis_id} with status {status}")
        if analysis_id in self._analyses:
            self._analyses[analysis_id]["end_time"] = datetime.now()
            self._analyses[analysis_id]["status"] = status
        else:
            logger.warning(f"SystemMonitor Warning: end_analysis called for unknown id {analysis_id}")

    def get_health_metrics(self):
        """Provide system health metrics (placeholder)."""
        logger.debug("SystemMonitor: Getting health metrics")
        try:
            cpu = psutil.cpu_percent()
            memory = psutil.virtual_memory().percent
        except Exception as e:
            logger.error(f"Failed to get system metrics: {e}")
            cpu = None
            memory = None
        return {"cpu_usage": cpu, "memory_usage_percent": memory, "component_statuses": self.metrics.get("component_status", {})}

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
