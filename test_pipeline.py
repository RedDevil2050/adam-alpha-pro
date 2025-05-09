import sys
import os
import asyncio
import pytest # Add pytest

sys.path.append(os.path.abspath("."))

from backend.orchestrator import run_full_cycle

@pytest.mark.asyncio # Add decorator
async def test():
    result = await run_full_cycle("TCS")
    print("PIPELINE TEST RESULT:", result)

asyncio.run(test())
