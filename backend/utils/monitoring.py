from datetime import datetime
from typing import Dict, Optional

class SystemMonitor:
    def __init__(self):
        self.components = {}
        self.analysis_timings = {}
        self.start_time = datetime.now()
        self._initialize_metrics()

    def _initialize_metrics(self):
        self.metrics = {
            "cpu_samples": [],
            "memory_samples": [],
            "error_counts": {},
            "component_status": {}
        }

    def register_component(self, component_name: str):
        self.components[component_name] = {
            "status": "healthy",
            "last_error": None,
            "error_count": 0
        }

    def is_ready(self) -> Dict:
        return {
            "ready": all(comp["status"] == "healthy" for comp in self.components.values()),
            "components": {name: comp["status"] for name, comp in self.components.items()}
        }
