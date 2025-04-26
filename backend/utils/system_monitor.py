from datetime import datetime
from typing import Dict, Optional
import psutil

class SystemMonitor:
    def __init__(self):
        self.components = {}
        self.start_time = datetime.now()
        self._initialize_metrics()

    def _initialize_metrics(self):
        self.metrics = {
            "cpu_samples": [],
            "memory_samples": [],
            "error_counts": {},
            "component_status": {}
        }

    def is_ready(self) -> Dict:
        return {
            "ready": all(comp["status"] == "healthy" for comp in self.components.values()),
            "components": {name: comp["status"] for name, comp in self.components.items()}
        }

    def check_system_health(self) -> Dict:
        return {"status": "healthy", "cpu": psutil.cpu_percent(), "memory": psutil.virtual_memory().percent}
