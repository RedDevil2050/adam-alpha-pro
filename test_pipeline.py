import sys
import os
import asyncio
import pytest # Add pytest

sys.path.append(os.path.abspath("."))

from backend.orchestrator import run_full_cycle

@pytest.mark.asyncio # Add decorator
async def test():
    # Test with MOSCHIP in correct NSE format
    result = await run_full_cycle("MOSCHIP.NS")
    print("PIPELINE TEST RESULT:", result)

asyncio.run(test())
