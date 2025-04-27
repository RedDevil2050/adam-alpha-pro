from abc import ABC, abstractmethod
from ..monitoring.metrics import agent_execution_time, agent_errors
from ..utils.cache_utils import cache_data

class AgentBase(ABC):
    def __init__(self, category: str):
        self.category = category
    
    @abstractmethod
    @cache_data()
    async def analyze(self, symbol: str) -> dict:
        """Implement analysis logic in subclasses"""
        pass
    
    async def run(self, symbol: str) -> dict:
        try:
            with agent_execution_time.labels(
                agent=self.__class__.__name__,
                category=self.category
            ).time():
                return await self.analyze(symbol)
        except Exception as e:
            agent_errors.labels(
                agent=self.__class__.__name__,
                error=type(e).__name__
            ).inc()
            raise
