import os
import pkgutil
import importlib
import inspect
import asyncio
from backend.utils.agent_metrics_definitions import instrument_agent
from backend.brain import Brain
from backend.utils.loguru_setup import logger

def discover_agents():
    agents = []
    pkg = 'backend.agents'
    pkg_path = os.path.join(os.path.dirname(__file__), '..', 'agents')
    for finder, name, ispkg in pkgutil.walk_packages(path=[os.path.abspath(pkg_path)], prefix=pkg + '.'):
        try:
            module = importlib.import_module(name)
            func = getattr(module, 'run', None)
            if inspect.iscoroutinefunction(func):
                alias = name.split('.')[-1]
                agents.append((alias, func))
        except ModuleNotFoundError:
            continue
    return agents

agent_calls = discover_agents()

async def run_single_agent(symbol: str, results: dict, func, name: str):
    try:
    instrumented = instrument_agent(name)(func)
    result = await instrumented(symbol, results)
    results[name] = result
        results[name] = result
    except Exception as e:
        logger.error(f"Agent {name} failed: {e}")
        results[name] = {"verdict": "avoid", "confidence": 0.0, "error": str(e)}

async def run_orchestration(symbol: str) -> dict:
    results = {}
    await asyncio.gather(*(run_single_agent(symbol, results, func, name) for name, func in agent_calls))
    try:
        results['brain'] = await Brain.compute_final_verdict(results)
    except Exception as e:
        logger.error(f"Brain failed: {e}")
        results["brain"] = {"verdict": "avoid", "confidence": 0.0, "error": str(e)}
    results["symbol"] = symbol
    return results

async def run_full_cycle(symbols: list[str]) -> list[dict]:
    return await asyncio.gather(*(run_orchestration(sym) for sym in symbols))