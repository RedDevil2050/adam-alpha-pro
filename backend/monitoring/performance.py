import time
import psutil
import functools
from prometheus_client import Histogram, Counter, Gauge

# Metrics
REQUEST_DURATION = Histogram(
    'request_duration_seconds',
    'Time spent processing request',
    ['endpoint']
)

MEMORY_USAGE = Gauge(
    'memory_usage_bytes',
    'Memory usage of operation',
    ['operation']
)

# Add a new metric for tracking API call failures
API_FAILURES = Counter(
    'api_failures_total',
    'Total number of API call failures',
    ['endpoint']
)

def monitor_execution_time(operation: str):
    """Decorator to monitor execution time of operations"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                REQUEST_DURATION.labels(operation).observe(duration)
        return wrapper
    return decorator

def track_memory_usage():
    """Decorator to track memory usage of operations"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            process = psutil.Process()
            mem_before = process.memory_info().rss
            
            try:
                result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
                return result
            finally:
                mem_after = process.memory_info().rss
                mem_used = mem_after - mem_before
                MEMORY_USAGE.labels(func.__name__).set(mem_used)
        return wrapper
    return decorator

def monitor_api_failures(endpoint: str):
    """Decorator to monitor API call failures"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            except Exception as e:
                API_FAILURES.labels(endpoint).inc()
                raise e
        return wrapper
    return decorator
