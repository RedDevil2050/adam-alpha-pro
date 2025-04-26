from prometheus_client import Counter, Histogram, Gauge
import functools
import time
from typing import Callable

# Metrics
AGENT_LATENCY = Histogram("agent_latency_seconds", "Agent execution time", ["agent_name"])
ERROR_COUNTER = Counter("agent_errors_total", "Total agent errors", ["agent_name", "error_type"])
DATA_QUALITY = Gauge("data_quality_score", "Data quality metric", ["source"])
PREDICTION_ACCURACY = Gauge("prediction_accuracy", "Agent prediction accuracy", ["agent_name"])

def monitor_agent(func: Callable) -> Callable:
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.time()
        try:
            result = await func(*args, **kwargs)
            AGENT_LATENCY.labels(func.__name__).observe(time.time() - start)
            return result
        except Exception as e:
            ERROR_COUNTER.labels(func.__name__, type(e).__name__).inc()
            raise
    return wrapper
