import asyncio
import aiohttp
from backend.data.providers.unified_provider import UnifiedDataProvider

provider = UnifiedDataProvider()

async def fetch_esg_data(symbol: str):
    """
    Fetch ESG data for a given symbol.

    Args:
        symbol: Ticker symbol to fetch ESG data for.

    Returns:
        Dictionary with ESG data.
    """
    return await provider.fetch_data_resilient(symbol, "esg")

async def fetch_historical_price_series(symbol: str, start_date: str, end_date: str, interval: str = "1d"):
    """
    Fetch historical price series for a given symbol.

    Args:
        symbol: Ticker symbol to fetch data for.
        start_date: Start date for historical data.
        end_date: End date for historical data.
        interval: Data interval (e.g., "1d" for daily).

    Returns:
        DataFrame with historical price data.
    """
    return await provider.fetch_price_data(symbol, start_date, end_date, interval)

async def fetch_alpha_vantage(symbol: str):
    """
    Fetch data from Alpha Vantage for a given symbol.

    Args:
        symbol: Ticker symbol to fetch data for.

    Returns:
        Dictionary with Alpha Vantage data.
    """
    return await provider._fetch_alpha_vantage(symbol, "price")

async def fetch_latest_bvps(symbol: str):
    """
    Fetch the latest book value per share (BVPS) for a given symbol.

    Args:
        symbol: Ticker symbol to fetch BVPS for.

    Returns:
        Dictionary with BVPS data.
    """
    return await provider.fetch_company_info(symbol)

async def fetch_eps_data(symbol: str):
    """
    Fetch the earnings per share (EPS) data for a given symbol.

    Args:
        symbol: Ticker symbol to fetch EPS data for.

    Returns:
        Dictionary with EPS data.
    """
    return await provider.fetch_company_info(symbol)

async def fetch_ohlcv_series(symbol: str, start_date: str, end_date: str, interval: str = "1d"):
    """
    Fetch OHLCV (Open, High, Low, Close, Volume) data for a given symbol.

    Args:
        symbol: Ticker symbol to fetch OHLCV data for.
        start_date: Start date for OHLCV data.
        end_date: End date for OHLCV data.
        interval: Data interval (e.g., "1d" for daily).

    Returns:
        DataFrame with OHLCV data.
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

async def fetch_price_series(symbol: str, source_preference: list = None, period: str = "1y"):
    """
    Fetch price series for a given symbol from preferred sources.

    Args:
        symbol: Ticker symbol to fetch data for.
        source_preference: List of preferred data sources (e.g., ["api", "scrape"]).
        period: Time period for the price series (e.g., "1y" for one year).

    Returns:
        DataFrame with price series data.
    """
    if source_preference is None:
        source_preference = ["api"]

    for source in source_preference:
        try:
            if source == "api":
                return await provider.fetch_price_data(symbol, period=period)
            elif source == "scrape":
                return await provider.scrape_price_data(symbol, period=period)
        except Exception as e:
            continue

    raise ValueError(f"Failed to fetch price series for {symbol} from all sources.")

async def fetch_book_value(symbol: str):
    """
    Fetch the book value for a given symbol.

    Args:
        symbol: Ticker symbol to fetch book value for.

    Returns:
        Dictionary with book value data.
    """
    return await provider.fetch_company_info(symbol, "book_value")

async def fetch_latest_eps(symbol: str):
    """
    Fetch the latest earnings per share (EPS) for a given symbol.

    Args:
        symbol: Ticker symbol to fetch EPS for.

    Returns:
        Dictionary with EPS data.
    """
    return await provider.fetch_company_info(symbol, "eps")

async def fetch_iex(symbol: str):
    """
    Fetch data from IEX for a given symbol.

    Args:
        symbol: Ticker symbol to fetch data for.

    Returns:
        Dictionary with IEX data.
    """
    return await provider.fetch_data_resilient(symbol, "iex")

async def fetch_sales_per_share(symbol: str):
    """
    Fetch the sales per share for a given symbol.

    Args:
        symbol: Ticker symbol to fetch sales per share for.

    Returns:
        Dictionary with sales per share data.
    """
    return await provider.fetch_company_info(symbol, "sales_per_share")

async def fetch_fcf_per_share(symbol: str):
    """
    Fetch the free cash flow (FCF) per share for a given symbol.

    Args:
        symbol: Ticker symbol to fetch FCF per share for.

    Returns:
        Dictionary with FCF per share data.
    """
    return await provider.fetch_company_info(symbol, "fcf_per_share")

async def fetch_market_data(symbol: str):
    """
    Fetch market data for a given symbol.

    Args:
        symbol: Ticker symbol to fetch market data for.

    Returns:
        Dictionary with market data.
    """
    return await provider.fetch_data_resilient(symbol, "market_data")

async def fetch_price_trendlyne(symbol: str):
    """
    Fetch price data from Trendlyne for a given symbol.

    Args:
        symbol: Ticker symbol to fetch data for.

    Returns:
        Dictionary with Trendlyne price data.
    """
    return await provider.fetch_data_resilient(symbol, "trendlyne")

async def fetch_eps(symbol: str):
    """
    Fetch earnings per share (EPS) for a given symbol.

    Args:
        symbol: Ticker symbol to fetch EPS for.

    Returns:
        Dictionary with EPS data.
    """
    return await provider.fetch_company_info(symbol, "eps")

async def fetch_latest_ev(symbol: str):
    """
    Fetch the latest enterprise value (EV) for a given symbol.

    Args:
        symbol: Ticker symbol to fetch EV for.

    Returns:
        Dictionary with EV data.
    """
    return await provider.fetch_company_info(symbol, "enterprise_value")

async def fetch_price_tickertape(symbol: str):
    """
    Fetch price data from Tickertape for a given symbol.

    Args:
        symbol: Ticker symbol to fetch data for.

    Returns:
        Dictionary with Tickertape price data.
    """
    return await provider.fetch_data_resilient(symbol, "tickertape")

async def fetch_latest_ebitda(symbol: str):
    """
    Fetch the latest EBITDA (Earnings Before Interest, Taxes, Depreciation, and Amortization) for a given symbol.

    Args:
        symbol: Ticker symbol to fetch EBITDA for.

    Returns:
        Dictionary with EBITDA data.
    """
    return await provider.fetch_company_info(symbol, "ebitda")

async def fetch_price_moneycontrol(symbol: str):
    """
    Fetch price data from Moneycontrol for a given symbol.

    Args:
        symbol: Ticker symbol to fetch data for.

    Returns:
        Dictionary with Moneycontrol price data.
    """
    return await provider.fetch_data_resilient(symbol, "moneycontrol")

async def fetch_historical_ev(symbol: str, start_date: str, end_date: str):
    """
    Fetch historical enterprise value (EV) data for a given symbol.

    Args:
        symbol: Ticker symbol to fetch EV data for.
        start_date: Start date for historical data.
        end_date: End date for historical data.

    Returns:
        DataFrame with historical EV data.
    """
    return await provider.fetch_historical_data(symbol, "enterprise_value", start_date, end_date)

async def fetch_price_stockedge(symbol: str):
    """
    Fetch price data from StockEdge for a given symbol.

    Args:
        symbol: Ticker symbol to fetch data for.

    Returns:
        Dictionary with StockEdge price data.
    """
    return await provider.fetch_data_resilient(symbol, "stockedge")

async def fetch_historical_ebitda(symbol: str, start_date: str, end_date: str):
    """
    Fetch historical EBITDA (Earnings Before Interest, Taxes, Depreciation, and Amortization) data for a given symbol.

    Args:
        symbol: Ticker symbol to fetch EBITDA data for.
        start_date: Start date for historical data.
        end_date: End date for historical data.

    Returns:
        DataFrame with historical EBITDA data.
    """
    return await provider.fetch_historical_data(symbol, "ebitda", start_date, end_date)

async def fetch_price_tradingview(symbol: str):
    """
    Fetch price data from TradingView for a given symbol.

    Args:
        symbol: Ticker symbol to fetch data for.

    Returns:
        Dictionary with TradingView price data.
    """
    return await provider.fetch_data_resilient(symbol, "tradingview")

async def fetch_price_alpha_vantage(symbol: str):
    """
    Fetch the latest price for a given symbol from Alpha Vantage.

    Args:
        symbol: Ticker symbol to fetch the price for.

    Returns:
        A dictionary containing the latest price or an error message.
    """
    api_key = "your_alpha_vantage_api_key"  # Replace with actual API key
    base_url = "https://www.alphavantage.co/query"
    params = {
        "function": "GLOBAL_QUOTE",
        "symbol": symbol,
        "apikey": api_key,
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(base_url, params=params) as response:
            if response.status != 200:
                return {"error": f"HTTP error {response.status}"}

            data = await response.json()
            if "Global Quote" in data and "05. price" in data["Global Quote"]:
                return {"price": float(data["Global Quote"]["05. price"])}

            return {"error": "Price data not found in response"}