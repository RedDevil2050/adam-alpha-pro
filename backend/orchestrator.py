from backend.utils.monitoring import monitor_agent
from backend.utils.circuit_breaker import CircuitBreaker
from backend.config.settings import settings
import asyncio

circuit_breaker = CircuitBreaker()

@monitor_agent
async def run_orchestration(symbol: str) -> dict:
    if not circuit_breaker.check_circuit("market_data"):
        raise RuntimeError("Market data service circuit breaker open")

    try:
        # Validate symbol
        if not isinstance(symbol, str) or len(symbol) > 10:
            raise ValueError("Invalid symbol format")

        # Rate limiting
        await asyncio.sleep(settings.RATE_LIMIT_DELAY)

        # ...existing orchestration code...

    except Exception as e:
        circuit_breaker.record_failure("market_data")
        raise