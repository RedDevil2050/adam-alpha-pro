import asyncio
from backend.data.providers.unified_provider import UnifiedDataProvider

provider = UnifiedDataProvider()

async def fetch_price_series(symbol: str, start_date: str, end_date: str, interval: str = "1d"):
    """
    Fetch historical price data for a given symbol.

    Args:
        symbol: Ticker symbol to fetch data for.
        start_date: Start date for historical data.
        end_date: End date for historical data.
        interval: Data interval (e.g., "1d" for daily).

    Returns:
        DataFrame with historical price data.
    """
    return await provider.fetch_price_data(symbol, start_date, end_date, interval)

async def fetch_price_point(symbol: str):
    """
    Fetch the latest price point for a given symbol.

    Args:
        symbol: Ticker symbol to fetch the latest price for.

    Returns:
        Dictionary with the latest price data.
    """
    return await provider.fetch_quote(symbol)