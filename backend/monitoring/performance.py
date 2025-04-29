from prometheus_client import Counter, Histogram, Gauge

# Data collection resilience metrics
DATA_COLLECTION_ATTEMPTS = Counter(
    "data_collection_attempts_total",
    "Total number of data collection attempts",
    ["symbol", "data_type"]
)

DATA_SOURCE_SWITCHES = Counter(
    "data_source_switches_total",
    "Number of times collection switched from API to scraping",
    ["symbol", "from_source", "to_source"]
)

DATA_QUALITY_GAUGE = Gauge(
    "data_quality",
    "Quality/confidence level of collected data",
    ["symbol", "data_type", "source"]
)

COLLECTION_LATENCY = Histogram(
    "data_collection_latency_seconds",
    "Latency for data collection including fallbacks",
    ["symbol", "data_type", "final_source"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

# Scraping failure metrics
SCRAPING_FAILURES = Counter(
    "scraping_failures_total",
    "Total number of web scraping failures",
    [
        "source",
        "error_type",
    ],  # source: tradingview, zerodha, etc. error_type: network, parse, timeout, etc.
)

# Data provider metrics
DATA_PROVIDER_FAILURES = Counter(
    "data_provider_failures_total",
    "Total number of data provider failures",
    ["provider", "endpoint", "error_type"],
)

DATA_PROVIDER_LATENCY = Histogram(
    "data_provider_latency_seconds",
    "Latency for data provider requests",
    ["provider", "endpoint"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
)

DATA_PROVIDER_AVAILABILITY = Gauge(
    "data_provider_availability", "Availability status of data providers", ["provider"]
)

# Cache metrics
CACHE_HITS = Counter(
    "cache_hits_total",
    "Total number of cache hits",
    ["cache_type"],  # redis, memory, etc.
)

CACHE_MISSES = Counter(
    "cache_misses_total", "Total number of cache misses", ["cache_type"]
)

# System health metrics
SYSTEM_HEALTH = Gauge(
    "system_health",
    "Overall system health status",
    ["component"],  # api, database, redis, etc.
)

AGENT_EXECUTION_SUCCESS = Counter(
    "agent_execution_success_total",
    "Total number of successful agent executions",
    ["agent_name", "category"],
)

AGENT_EXECUTION_FAILURES = Counter(
    "agent_execution_failures_total",
    "Total number of failed agent executions",
    ["agent_name", "category", "error_type"],
)


def increment_scraping_failure(source: str, error_type: str = "unknown"):
    """Record a scraping failure"""
    SCRAPING_FAILURES.labels(source=source, error_type=error_type).inc()


def record_provider_latency(provider: str, endpoint: str, duration: float):
    """Record latency for a data provider request"""
    DATA_PROVIDER_LATENCY.labels(provider=provider, endpoint=endpoint).observe(duration)


def record_provider_failure(provider: str, endpoint: str, error_type: str):
    """Record a data provider failure"""
    DATA_PROVIDER_FAILURES.labels(
        provider=provider, endpoint=endpoint, error_type=error_type
    ).inc()
    # Update availability status
    DATA_PROVIDER_AVAILABILITY.labels(provider=provider).set(0)


def record_provider_success(provider: str):
    """Record a successful data provider operation"""
    DATA_PROVIDER_AVAILABILITY.labels(provider=provider).set(1)


def record_cache_hit(cache_type: str = "redis"):
    """Record a cache hit"""
    CACHE_HITS.labels(cache_type=cache_type).inc()


def record_cache_miss(cache_type: str = "redis"):
    """Record a cache miss"""
    CACHE_MISSES.labels(cache_type=cache_type).inc()


def update_system_health(component: str, healthy: bool):
    """Update system health status"""
    SYSTEM_HEALTH.labels(component=component).set(1 if healthy else 0)


def record_agent_success(agent_name: str, category: str):
    """Record successful agent execution"""
    AGENT_EXECUTION_SUCCESS.labels(agent_name=agent_name, category=category).inc()


def record_agent_failure(agent_name: str, category: str, error_type: str):
    """Record failed agent execution"""
    AGENT_EXECUTION_FAILURES.labels(
        agent_name=agent_name, category=category, error_type=error_type
    ).inc()


def record_collection_attempt(symbol: str, data_type: str):
    """Record a data collection attempt"""
    DATA_COLLECTION_ATTEMPTS.labels(symbol=symbol, data_type=data_type).inc()

def record_source_switch(symbol: str, from_source: str, to_source: str):
    """Record when collection switches from one source to another"""
    DATA_SOURCE_SWITCHES.labels(
        symbol=symbol,
        from_source=from_source,
        to_source=to_source
    ).inc()

def record_data_quality(symbol: str, data_type: str, source: str, confidence: float):
    """Record the quality/confidence of collected data"""
    DATA_QUALITY_GAUGE.labels(symbol=symbol, data_type=data_type, source=source).set(confidence)

def record_collection_latency(symbol: str, data_type: str, source: str, duration: float):
    """Record the total time taken to collect data"""
    COLLECTION_LATENCY.labels(
        symbol=symbol,
        data_type=data_type,
        final_source=source
    ).observe(duration)
