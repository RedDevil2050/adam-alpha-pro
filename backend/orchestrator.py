import asyncio
from typing import Dict, List, Type, Optional
from datetime import datetime
from backend.agents.base import AgentBase
from backend.utils.logger import get_logger

logger = get_logger(__name__)

class Orchestrator:
    def __init__(self):
        self._agents: Dict[str, Type[AgentBase]] = {}
        self._dependencies: Dict[str, List[str]] = {}
        self._execution_times: Dict[str, float] = {}
        self.context: Dict = {}
        
    def register(self, name: str, agent_class: Type[AgentBase]) -> None:
        """Register an agent with dependencies"""
        self._agents[name] = agent_class
        agent = agent_class()
        self._dependencies[name] = agent.get_dependencies()

    async def execute_agent(self, name: str, symbol: str) -> Optional[Dict]:
        """Execute single agent with timing"""
        if name not in self._agents:
            logger.error(f"Agent {name} not found")
            return None
            
        start = datetime.now()
        agent = self._agents[name]()
        try:
            await agent.pre_execute(symbol, self.context)
            result = await agent.execute(symbol, self.context)
            if agent.validate_result(result):
                await agent.post_execute(result, self.context)
                self._execution_times[name] = (datetime.now() - start).total_seconds()
                return result
        except Exception as e:
            logger.error(f"Agent {name} execution failed: {e}")
        return None

    async def execute_all(self, symbol: str) -> Dict[str, Dict]:
        """Execute all agents respecting dependencies"""
        self.context = {}
        results = {}
        
        # Build execution order
        execution_order = self._build_execution_order()
        
        # Execute in order
        for name in execution_order:
            result = await self.execute_agent(name, symbol)
            if result:
                results[name] = result
                self.context[name] = result
                
        return results

    def _build_execution_order(self) -> List[str]:
        """Build execution order respecting dependencies"""
        ordered = []
        visited = set()
        
        def visit(name: str):
            if name in visited:
                return
            visited.add(name)
            for dep in self._dependencies[name]:
                visit(dep)
            ordered.append(name)
            
        for name in self._agents:
            visit(name)
            
        return ordered

    def get_metrics(self) -> Dict:
        """Get execution metrics"""
        return {
            'execution_times': self._execution_times,
            'agent_count': len(self._agents),
            'last_run': datetime.now().isoformat()
        }

async def run(symbol: str) -> Dict[str, Dict]:
    """Run the orchestrator for a given symbol."""
    orchestrator = Orchestrator()
    # Register agents here (example):
    # orchestrator.register("example_agent", ExampleAgent)
    results = await orchestrator.execute_all(symbol)
    logger.info(f"Execution results for {symbol}: {results}")
    return results

def run_full_cycle():
    """Run the full cycle of the orchestrator."""
    print("Running full cycle...")

def run_orchestration(symbol: str) -> dict:
    """Simulate running the orchestration process for a given symbol."""
    return {"symbol": symbol, "status": "orchestration complete"}