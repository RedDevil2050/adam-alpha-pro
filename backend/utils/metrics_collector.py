from typing import Dict
import numpy as np
from datetime import datetime

class MetricsCollector:
    def __init__(self):
        self.metrics = {
            "category_executions": {},
            "response_times": [],
            "error_rates": {},
            "cache_hits": 0,
            "cache_misses": 0,
            "start_time": datetime.now()
        }

    def record_category_execution(self, category: str, result_size: int, had_error: bool):
        if category not in self.metrics["category_executions"]:
            self.metrics["category_executions"][category] = {
                "count": 0,
                "errors": 0,
                "avg_size": 0
            }
        
        stats = self.metrics["category_executions"][category]
        stats["count"] += 1
        if had_error:
            stats["errors"] += 1
        stats["avg_size"] = (stats["avg_size"] * (stats["count"] - 1) + result_size) / stats["count"]

    def record_response_time(self, duration: float):
        self.metrics["response_times"].append(duration)
        if len(self.metrics["response_times"]) > 1000:
            self.metrics["response_times"] = self.metrics["response_times"][-1000:]

    def record_cache_event(self, hit: bool):
        if hit:
            self.metrics["cache_hits"] += 1
        else:
            self.metrics["cache_misses"] += 1

    def get_metrics(self) -> Dict:
        return {
            "performance": {
                "avg_response_time": np.mean(self.metrics["response_times"]) if self.metrics["response_times"] else 0,
                "p95_response_time": np.percentile(self.metrics["response_times"], 95) if self.metrics["response_times"] else 0,
                "cache_hit_ratio": self.metrics["cache_hits"] / (self.metrics["cache_hits"] + self.metrics["cache_misses"]) if (self.metrics["cache_hits"] + self.metrics["cache_misses"]) > 0 else 0
            },
            "category_stats": self.metrics["category_executions"],
            "uptime_seconds": (datetime.now() - self.metrics["start_time"]).total_seconds()
        }
