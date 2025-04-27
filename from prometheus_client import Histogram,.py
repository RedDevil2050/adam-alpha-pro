from prometheus_client import Histogram, Counter, Gauge
from functools import wraps
import time
import psutil

# Performance metrics
request_duration = Histogram(
    'request_duration_seconds',
    'Request duration in seconds',
    ['endpoint']
)

system_memory = Gauge(
    'system_memory_usage_percent',
    'System memory usage percentage'
)

system_cpu = Gauge(
    'system_cpu_usage_percent',
    'System CPU usage percentage'
)

def monitor_performance(endpoint: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            # Update system metrics
            system_memory.set(psutil.virtual_memory().percent)
            system_cpu.set(psutil.cpu_percent())
            
            result = await func(*args, **kwargs)
            
            # Record request duration
            request_duration.labels(endpoint=endpoint).observe(
                time.time() - start_time
            )
            
            return result
        return wrapper
    return decorator
