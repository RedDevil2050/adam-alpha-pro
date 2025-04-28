from prometheus_client import Histogram, Counter, Gauge
from loguru import logger

AGENT_DURATION = Histogram(
    "agent_execution_duration_seconds", "Time taken by each agent", ["agent"]
)
AGENT_ERRORS = Counter("agent_errors_total", "Number of errors per agent", ["agent"])
CATEGORY_SCORE = Gauge(
    "brain_category_score", "Average score by category", ["category"]
)
FINAL_SCORE = Gauge("brain_final_score", "Final composite score from Brain")

import time


def instrument_agent(agent_name: str):
    def decorator(coro):
        async def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                res = await coro(*args, **kwargs)
                AGENT_DURATION.labels(agent=agent_name).observe(
                    time.perf_counter() - start
                )
                return res
            except Exception as e:
                AGENT_ERRORS.labels(agent=agent_name).inc()
                logger.error(f"Agent {agent_name} error: {e}")
                raise

        return wrapper

    return decorator
