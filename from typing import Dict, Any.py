from typing import Dict, Any
from ..monitoring.metrics import metrics_collector
import aiohttp

async def fetch_market_data(symbol: str) -> Dict[str, Any]:
    """Fetch market data using dual-channel framework (API + Scraping)."""
    try:
        # Primary API source
        data = await fetch_from_primary_api(symbol)
        if validate_market_data(data):
            return data
        metrics_collector.record_error("data_provider", "Invalid data from primary API")
    except Exception as e:
        metrics_collector.record_error("data_provider", f"Primary API failed: {str(e)}")

    # Fallback to scraping
    try:
        data = await scrape_market_data(symbol)
        if validate_market_data(data):
            return data
        metrics_collector.record_error("data_provider", "Invalid data from scraping")
    except Exception as e:
        metrics_collector.record_error("data_provider", f"Scraping failed: {str(e)}")

    raise ValueError(f"Failed to fetch market data for {symbol} from both channels.")

async def fetch_from_primary_api(symbol: str) -> Dict[str, Any]:
    """Fetch market data from the primary API."""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.example.com/market-data/{symbol}") as response:
            if response.status != 200:
                raise ValueError(f"Primary API returned status {response.status}")
            return await response.json()

async def scrape_market_data(symbol: str) -> Dict[str, Any]:
    """Scrape market data as a fallback."""
    # Mocked scraping logic
    return {
        "price": 150.0,
        "volume": 1000000,
        "timestamp": "2024-01-20T12:00:00Z"
    }

def validate_market_data(data: Dict[str, Any]) -> bool:
    """Validate the structure and content of market data."""
    required_fields = ["price", "volume", "timestamp"]
    return all(field in data and data[field] is not None for field in required_fields)