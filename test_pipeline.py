
import sys
import os
import asyncio

sys.path.append(os.path.abspath("."))

from backend.orchestrator import run

async def test():
    result = await run("TCS")
    print("PIPELINE TEST RESULT:", result)

asyncio.run(test())
