import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import asyncio
from unittest.mock import AsyncMock, patch # Import patch
from backend.utils.data_provider import (
    fetch_price_trendlyne, fetch_price_tickertape,
    fetch_price_moneycontrol, fetch_price_stockedge,
    fetch_price_tradingview,
    provider # Import the provider instance
)

@pytest.mark.asyncio
async def test_trendlyne(monkeypatch):
    # Mock the provider's fetch_data_resilient method
    # This mock is specific to the call made by fetch_price_trendlyne("INFY")
    # Assuming fetch_data_resilient might be a staticmethod or called in a way that 'slf' is not the instance
    async def mock_fetch_data_resilient_custom(symbol_arg, data_type_arg, **kwargs_arg):
        # fetch_price_trendlyne("INFY") calls:
        # provider.fetch_data_resilient("INFY", "price", provider_override="trendlyne")
        if (
            symbol_arg == "INFY" and
            data_type_arg == "price" and
            kwargs_arg.get("provider_override") == "trendlyne"
        ):
            return 100.0  # Return a float, as expected by the assertion
        
        # If the mock is called with unexpected arguments, raise an error to make the test fail clearly.
        # This helps in debugging if the call signature changes or if the mock is too broad.
        raise AssertionError(
            f"mock_fetch_data_resilient_custom called with unexpected arguments: "
            f"symbol='{symbol_arg}', data_type='{data_type_arg}', kwargs={kwargs_arg}"
        )

    # Use monkeypatch to replace the method on the *instance* of UnifiedDataProvider
    monkeypatch.setattr(provider, 'fetch_data_resilient', mock_fetch_data_resilient_custom)

    result = await fetch_price_trendlyne("INFY")

    # Assert that the result is a float and equals the mocked value
    assert isinstance(result, float), f"Expected float, got {type(result)}: {result}"
    assert result == 100.0

