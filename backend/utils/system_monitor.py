from datetime import datetime
from typing import Dict, Optional
import psutil


class SystemMonitor:
    def __init__(self):
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
