
import sys, os, asyncio
sys.path.append(os.path.abspath("."))

from backend.orchestrator import run

symbols = ["TCS", "INFY", "RELIANCE", "ITC", "HDFCBANK"]

async def main():
    for sym in symbols:
        result = await run(sym)
        print(f"RESULT for {sym}:\n", result, "\n")

asyncio.run(main())
