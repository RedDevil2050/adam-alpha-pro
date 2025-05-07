import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import asyncio
from unittest.mock import AsyncMock # Import AsyncMock
from backend.utils.data_provider import (
    fetch_price_trendlyne, fetch_price_tickertape,
    fetch_price_moneycontrol, fetch_price_stockedge,
    fetch_price_tradingview,
    provider # Import the provider instance
)

@pytest.mark.asyncio
async def test_trendlyne(monkeypatch):
    # Improved mock response class (might not be strictly needed with the new mocking strategy)
    class MockResponse:
        def __init__(self, text, status_code=200):
            self.text = text
            self.status_code = status_code
            # Add async json method to mimic httpx.Response
            async def json():
                import json
                return json.loads(self.text) # If Trendlyne returned JSON
            self.json = json

    # Mock the provider's fetch_data_resilient method for the 'trendlyne' case
    original_fetch_data_resilient = provider.fetch_data_resilient
    # Corrected mock signature to match UnifiedDataProvider.fetch_data_resilient
    async def mock_fetch_data_resilient_for_trendlyne(slf, provider_name_arg, symbol_arg, data_type_arg, **kwargs_arg):
        if provider_name_arg == "trendlyne" and symbol_arg == "INFY" and data_type_arg == "price":
            # This simulates the successful outcome of fetching and parsing Trendlyne data
            return 100.0
        # Fallback to original for other calls (ensure it's used correctly if needed)
        # For this specific test, we only expect the INFY/trendlyne/price call.
        # If other calls were made to this mock, they would hit the original_fetch_data_resilient.
        # Consider raising an error for unexpected calls if the test is narrowly focused.
        return await original_fetch_data_resilient(slf, provider_name_arg, symbol_arg, data_type_arg, **kwargs_arg)

    monkeypatch.setattr(provider, 'fetch_data_resilient', mock_fetch_data_resilient_for_trendlyne)

    result = await fetch_price_trendlyne("INFY")

    # Assert that the result is a float and equals the mocked value
    assert isinstance(result, float), f"Expected float, got {type(result)}: {result}"
    assert result == 100.0

