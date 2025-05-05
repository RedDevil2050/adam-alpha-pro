import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import asyncio
from unittest.mock import AsyncMock # Import AsyncMock
from backend.utils.data_provider import (
    fetch_price_trendlyne, fetch_price_tickertape,
    fetch_price_moneycontrol, fetch_price_stockedge,
    fetch_price_tradingview
)

@pytest.mark.asyncio
async def test_trendlyne(monkeypatch):
    # Improved mock response class
    class MockResponse:
        def __init__(self, text, status_code=200):
            self.text = text
            self.status_code = status_code

        # Add other methods/attributes if needed by the parsing logic
        # e.g., async def json(self): return json.loads(self.text)

    # Mock the get method to return an instance of MockResponse
    async def mock_get(self, url):
        # Simulate the expected HTML structure
        html_text = "<div class='company-header__LTP'>100.0</div>"
        return MockResponse(html_text)

    monkeypatch.setattr("httpx.AsyncClient.get", mock_get)
    result = await fetch_price_trendlyne("INFY")

    # Assert that the result is a float and equals the mocked value
    assert isinstance(result, float)
    assert result == 100.0

