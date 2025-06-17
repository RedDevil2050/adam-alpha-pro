import asyncio
from typing import List, Dict
from backend.agents.registry import AgentRegistry
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class AgentOrchestrator:
    def __init__(self):
        self.registry = AgentRegistry()
        self.execution_stats = {}

    async def execute_category(
        self, category: str, symbol: str, agent_outputs: Dict = {}
    ) -> List[Dict]:
        """Execute all agents in a category"""
        agents = self.registry.get_category_agents(category)
        tasks = []

        for name, agent_class in agents.items():
            agent = agent_class()
            task = asyncio.create_task(agent.execute(symbol, agent_outputs))
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r for r in results if isinstance(r, dict)]

    async def execute_pipeline(self, symbol: str) -> Dict[str, List[Dict]]:
        """Execute full agent pipeline"""
        categories = ["valuation", "technical", "fundamental", "sentiment"]
        outputs = {}

        for category in categories:
            try:
                results = await self.execute_category(category, symbol, outputs)
                outputs[category] = results
                self._update_stats(category, results)
            except Exception as e:
                logger.error(f"Category {category} execution failed: {e}")

        return outputs

    def _update_stats(self, category: str, results: List[Dict]):
        """Update execution statistics"""
        success = len([r for r in results if r.get("verdict") != "ERROR"])
        total = len(results)

        if category not in self.execution_stats:
            self.execution_stats[category] = {"success": 0, "total": 0}

        self.execution_stats[category]["success"] += success
        self.execution_stats[category]["total"] += total
