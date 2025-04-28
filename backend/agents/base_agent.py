from backend.utils.monitoring import monitor_agent
from backend.utils.circuit_breaker import CircuitBreaker
from abc import ABC, abstractmethod
from typing import Dict, Any
import time


class BaseAgent(ABC):
    def __init__(self):
        self.circuit_breaker = CircuitBreaker()
        self.last_run = 0
        self.min_interval = 1.0  # Minimum seconds between runs

    @monitor_agent
    async def execute(
        self, symbol: str, context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        # Rate limiting
        now = time.time()
        if now - self.last_run < self.min_interval:
            await asyncio.sleep(self.min_interval - (now - self.last_run))

        try:
            if not self.circuit_breaker.check_circuit(self.__class__.__name__):
                return {
                    "symbol": symbol,
                    "verdict": "CIRCUIT_OPEN",
                    "confidence": 0.0,
                    "value": None,
                    "details": {},
                    "error": "Circuit breaker open",
                    "agent_name": self.__class__.__name__,
                }

            result = await self.run(symbol, context)
            self.last_run = time.time()
            return result

        except Exception as e:
            self.circuit_breaker.record_failure(self.__class__.__name__)
            raise

    @abstractmethod
    async def run(self, symbol: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        pass
