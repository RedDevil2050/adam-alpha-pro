import asyncio
from backend.orchestrator import run_full_cycle
from loguru import logger

if __name__ == "__main__":
    asyncio.run(run_full_cycle())
