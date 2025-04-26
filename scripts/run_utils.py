import asyncio
from backend.orchestrator import run_orchestration, run_full_cycle

def run_all(symbol: str):
    result = asyncio.run(run_orchestration(symbol))
    print(result)
    return result

def run_stealth_agents(symbol: str):
    return run_all(symbol)

def run_full_pipeline(symbols: list[str]):
    results = asyncio.run(run_full_cycle(symbols))
    for r in results:
        print(r)
    return results