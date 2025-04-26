import psutil
import numpy as np
from datetime import datetime
from typing import Dict
from loguru import logger

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

    def start_analysis(self, analysis_id: str):
        self.analysis_timings[analysis_id] = {
            "start": datetime.now(),
            "steps": {}
        }
        self._sample_system_metrics()

    def end_analysis(self, analysis_id: str, status: str):
        if analysis_id in self.analysis_timings:
            duration = (datetime.now() - self.analysis_timings[analysis_id]["start"]).total_seconds()
            self.analysis_timings[analysis_id]["duration"] = duration
            self.analysis_timings[analysis_id]["status"] = status

    def _sample_system_metrics(self):
        try:
            self.metrics["cpu_samples"].append(psutil.cpu_percent())
            self.metrics["memory_samples"].append(psutil.virtual_memory().percent)
            
            if len(self.metrics["cpu_samples"]) > 100:
                self.metrics["cpu_samples"] = self.metrics["cpu_samples"][-100:]
                self.metrics["memory_samples"] = self.metrics["memory_samples"][-100:]
        except Exception as e:
            logger.error(f"Error sampling system metrics: {e}")

    def get_health_metrics(self) -> Dict:
        return {
            "system": {
                "cpu_usage": np.mean(self.metrics["cpu_samples"]) if self.metrics["cpu_samples"] else 0,
                "memory_usage": np.mean(self.metrics["memory_samples"]) if self.metrics["memory_samples"] else 0,
                "disk_usage": psutil.disk_usage('/').percent
            },
            "components": self.components,
            "recent_analyses": len(self.analysis_timings),
            "avg_analysis_time": np.mean([t["duration"] for t in self.analysis_timings.values() if "duration" in t]) if self.analysis_timings else 0
        }

    def check_system_health(self) -> Dict[str, str]:
        """Enhanced health check with recommendations"""
        metrics = self.get_health_metrics()
        health_status = {
            "status": "healthy",
            "warnings": [],
            "recommendations": []
        }

        # CPU Check
        if metrics["system"]["cpu_usage"] > 80:
            health_status["status"] = "degraded"
            health_status["warnings"].append("High CPU usage")
            health_status["recommendations"].append("Consider scaling horizontally")

        # Memory Check
        if metrics["system"]["memory_usage"] > 85:
            health_status["status"] = "degraded"
            health_status["warnings"].append("High memory usage")
            health_status["recommendations"].append("Increase memory allocation")

        # Error Rate Check
        error_rate = len([t for t in self.analysis_timings.values() 
                         if t.get("status") == "error"]) / max(len(self.analysis_timings), 1)
        if error_rate > 0.1:
            health_status["warnings"].append(f"High error rate: {error_rate:.2%}")
            health_status["recommendations"].append("Check error logs and agent stability")

        return health_status

    def _rotate_metrics_history(self):
        """Rotate metrics history to prevent memory bloat"""
        max_history = 1000
        if len(self.analysis_timings) > max_history:
            oldest_keys = sorted(self.analysis_timings.keys())[:len(self.analysis_timings) - max_history]
            for key in oldest_keys:
                del self.analysis_timings[key]

    def get_production_metrics(self) -> Dict:
        """Get detailed production metrics"""
        return {
            "system": self.get_health_metrics()["system"],
            "performance": {
                "request_success_rate": self._calculate_success_rate(),
                "avg_response_time": self._calculate_avg_response_time(),
                "error_rate": self._calculate_error_rate(),
                "cache_hit_ratio": self._calculate_cache_ratio()
            },
            "availability": {
                "uptime": self._calculate_uptime(),
                "last_incident": self._get_last_incident(),
                "degraded_services": self._get_degraded_services()
            },
            "resources": {
                "memory_trend": self._get_memory_trend(),
                "cpu_trend": self._get_cpu_trend(),
                "disk_usage_trend": self._get_disk_trend()
            }
        }

    def _calculate_success_rate(self) -> float:
        total = len(self.analysis_timings)
        if not total:
            return 1.0
        successes = len([t for t in self.analysis_timings.values() 
                        if t.get("status") == "success"])
        return successes / total

    def _calculate_avg_response_time(self) -> float:
        durations = [t.get("duration", 0) for t in self.analysis_timings.values()]
        return np.mean(durations) if durations else 0

    def _calculate_error_rate(self) -> float:
        total = len(self.analysis_timings)
        if not total:
            return 0.0
        errors = len([t for t in self.analysis_timings.values() if t.get("status") == "error"])
        return errors / total

    def _calculate_cache_ratio(self) -> float:
        return self.metrics.get("cache_hits", 0) / max(self.metrics.get("total_requests", 1), 1)

    def _calculate_uptime(self) -> float:
        return (datetime.now() - self.start_time).total_seconds()

    def _get_last_incident(self) -> Dict:
        incidents = sorted(
            [t for t in self.analysis_timings.values() if t.get("status") == "error"],
            key=lambda x: x["start"],
            reverse=True
        )
        return incidents[0] if incidents else None

    def _get_degraded_services(self) -> list:
        return [
            name for name, component in self.components.items()
            if component["status"] != "healthy"
        ]

    def _get_memory_trend(self) -> list:
        return self.metrics["memory_samples"][-10:]

    def _get_cpu_trend(self) -> list:
        return self.metrics["cpu_samples"][-10:]

    def _get_disk_trend(self) -> list:
        return self.metrics.get("disk_samples", [])[-10:]

    def is_ready(self) -> Dict[str, bool]:
        """Check if all system components are ready"""
        component_status = {
            name: info["status"] == "healthy"
            for name, info in self.components.items()
        }
        
        system_ready = all(component_status.values())
        metrics_ready = len(self.metrics["cpu_samples"]) > 0
        
        return {
            "ready": system_ready and metrics_ready,
            "components": component_status,
            "metrics_initialized": metrics_ready,
            "uptime": self._calculate_uptime()
        }

    def check_market_readiness(self) -> Dict:
        """Verify market system readiness"""
        return {
            "market_ready": all(c["status"] == "healthy" for c in self.components.values()),
            "system_health": self.check_system_health()["status"],
            "metrics_ready": len(self.metrics["cpu_samples"]) > 0,
            "resources_available": self._check_resources(),
            "market_status": "open" if self._is_market_hours() else "closed"
        }

    def _check_resources(self) -> bool:
        """Check if system has sufficient resources"""
        metrics = self.get_health_metrics()["system"]
        return (
            metrics["cpu_usage"] < 80 and
            metrics["memory_usage"] < 85 and
            metrics["disk_usage"] < 90
        )

    def _is_market_hours(self) -> bool:
        """Check if within market hours"""
        now = datetime.now()
        # Simplified market hours check (9:30 AM - 4:00 PM EST)
        market_open = now.replace(hour=9, minute=30, second=0)
        market_close = now.replace(hour=16, minute=0, second=0)
        return market_open <= now <= market_close
