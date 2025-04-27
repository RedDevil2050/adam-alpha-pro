from prometheus_client import Counter, Histogram, Gauge
from functools import wraps
import time

# Prometheus metrics
AGENT_EXECUTION_TIME = Histogram(
    'agent_execution_seconds',
    'Time spent executing agent analysis',
    ['agent_name', 'category']
)

AGENT_ERRORS = Counter(
    'agent_errors_total',
    'Total number of agent execution errors',
    ['agent_name', 'error_type']
)

AGENT_CONFIDENCE = Gauge(
    'agent_confidence',
    'Confidence level of agent analysis',
    ['agent_name']
)

def instrument_agent(category: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            start_time = time.time()
            agent_name = self.__class__.__name__
            
            try:
                result = await func(self, *args, **kwargs)
                AGENT_EXECUTION_TIME.labels(
                    agent_name=agent_name,
                    category=category
                ).observe(time.time() - start_time)
                
                if isinstance(result, dict) and 'confidence' in result:
                    AGENT_CONFIDENCE.labels(agent_name=agent_name).set(result['confidence'])
                
                return result
            except Exception as e:
                AGENT_ERRORS.labels(
                    agent_name=agent_name,
                    error_type=type(e).__name__
                ).inc()
                raise
        return wrapper
    return decorator
