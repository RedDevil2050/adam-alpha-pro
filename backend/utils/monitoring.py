from datetime import datetime
from typing import Dict, Optional


class SystemMonitor:
    def __init__(self):
        self.components = {}
        self.analysis_timings = {}
        self.start_time = datetime.now()
        self._initialize_metrics()
        self._health_statuses = {}

    def update_health(self, component_name: str, healthy: bool):
        """
        Updates the health status of a specific system component.
        """
        status_str = "Healthy" if healthy else "Unhealthy"
        self._health_statuses[component_name] = status_str

    def get_health_status(self, component_name: str):
        """Retrieve a component's health status (default "Unknown")."""
        return self._health_statuses.get(component_name, "Unknown")
