from fastapi import APIRouter, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CollectorRegistry, # Import CollectorRegistry
)
import time
import psutil

router = APIRouter()

# Use a specific registry to avoid conflicts with the default one
registry = CollectorRegistry()

# Define Prometheus metrics using the custom registry
REQUEST_COUNT = Counter(
    'zion_request_count',
    'App Request Count',
    ['app_name', 'method', 'endpoint', 'http_status'],
    registry=registry
)

REQUEST_LATENCY = Histogram(
    'zion_request_latency_seconds',
    'Request latency in seconds',
    ['app_name', 'endpoint'],
    registry=registry
)

ACTIVE_SESSIONS = Gauge(
    'zion_active_sessions',
    'Number of currently active user sessions',
    registry=registry
)

SYSTEM_CPU = Gauge(
    'zion_system_cpu_usage_percent',
    'Current system CPU usage in percent',
    registry=registry
)

SYSTEM_MEMORY = Gauge(
    'zion_system_memory_usage_percent',
    'Current system memory usage in percent',
    registry=registry
)

DATA_PROVIDER_REQUESTS = Counter(
    'zion_data_provider_requests_total',
    'Total data provider API requests',
    ['provider', 'status'],
    registry=registry
)

AGENT_EXECUTIONS = Counter(
    'zion_agent_executions_total',
    'Total number of agent executions',
    ['agent_name', 'status'],
    registry=registry
)

AGENT_EXECUTION_TIME = Histogram(
    'zion_agent_execution_time_seconds',
    'Time taken to execute an agent',
    ['agent_name'],
    registry=registry
)

CACHE_HITS = Counter(
    'zion_cache_hits_total',
    'Total number of cache hits',
    ['cache_type'],
    registry=registry
)

CACHE_MISSES = Counter(
    'zion_cache_misses_total',
    'Total number of cache misses',
    ['cache_type'],
    registry=registry
)


@router.get("/metrics", response_class=Response)
async def metrics():
    """
    Endpoint that serves Prometheus metrics about the application.
    """
    # Update system metrics on each request
    SYSTEM_CPU.set(psutil.cpu_percent(interval=None))
    SYSTEM_MEMORY.set(psutil.virtual_memory().percent)
    
    # Return metrics in Prometheus format using the custom registry
    return Response(content=generate_latest(registry), media_type=CONTENT_TYPE_LATEST)


# Utility function to track request metrics
def track_request_metrics(request, response, duration):
    """
    Track metrics for each request
    """
    REQUEST_COUNT.labels(
        'zion_market_analysis',
        request.method,
        request.url.path,
        response.status_code
    ).inc()
    
    REQUEST_LATENCY.labels(
        'zion_market_analysis',
        request.url.path
    ).observe(duration)


# Utility functions for custom metrics
def track_data_provider_request(provider: str, status: str = "success"):
    """
    Track data provider API request
    """
    DATA_PROVIDER_REQUESTS.labels(provider, status).inc()


def track_agent_execution(agent_name: str, execution_time: float, status: str = "success"):
    """
    Track agent execution metrics
    """
    AGENT_EXECUTIONS.labels(agent_name, status).inc()
    AGENT_EXECUTION_TIME.labels(agent_name).observe(execution_time)


def track_cache_operation(cache_type: str, hit: bool):
    """
    Track cache hit/miss
    """
    if hit:
        CACHE_HITS.labels(cache_type).inc()
    else:
        CACHE_MISSES.labels(cache_type).inc()


def set_active_sessions(count: int):
    """
    Set the number of active sessions
    """
    ACTIVE_SESSIONS.set(count)