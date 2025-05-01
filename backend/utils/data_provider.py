import asyncio
import aiohttp
import logging
from backend.data.providers.unified_provider import UnifiedDataProvider
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO) # Or use logging.DEBUG for more verbose output
logger = logging.getLogger(__name__)

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

async def fetch_alpha_vantage(symbol: str, data_type: str = "price"):
    """
    Fetch data from Alpha Vantage for a given symbol.

    Args:
        symbol: Ticker symbol to fetch data for.
        data_type: Type of data to fetch (defaults to "price").

    Returns:
        Dictionary with Alpha Vantage data.
    """
    return await provider._fetch_alpha_vantage(symbol, data_type)

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

    logger.debug(f"Attempting to fetch price series for {symbol} with preference {source_preference}")
    
    # Convert period to start_date and end_date format for fetch_price_data
    end_date = datetime.now().strftime("%Y-%m-%d")
    
    # Calculate start_date based on period
    if period.endswith('y'):
        years = int(period[:-1])
        start_date = (datetime.now() - timedelta(days=years*365)).strftime("%Y-%m-%d")
    elif period.endswith('m'):
        months = int(period[:-1])
        start_date = (datetime.now() - timedelta(days=months*30)).strftime("%Y-%m-%d")
    elif period.endswith('d'):
        days = int(period[:-1])
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    else:
        # Default to 1 year if period format is unknown
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    
    for source in source_preference:
        try:
            logger.debug(f"Trying source: {source} for {symbol}")
            if source == "api":
                # Use start_date and end_date directly
                data = await provider.fetch_price_data(symbol, start_date, end_date)
                if data is not None and not isinstance(data, dict) and not data.empty:
                    logger.debug(f"Successfully fetched from source: {source} for {symbol}")
                    return data
                else:
                    logger.warning(f"Source {source} returned empty/None data for {symbol}")
            elif source == "scrape":
                try:
                    # If you implement scrape_price_data in UnifiedDataProvider
                    data = await provider.scrape_price_data(symbol, start_date=start_date, end_date=end_date)
                    if data is not None and not isinstance(data, dict) and not data.empty:
                        logger.debug(f"Successfully fetched from source: {source} for {symbol}")
                        return data
                    else:
                        logger.warning(f"Source {source} returned empty/None data for {symbol}")
                except AttributeError:
                    logger.warning(f"scrape_price_data method not available in provider for {symbol}")
        except Exception as e:
            logger.error(f"Failed to fetch from source {source} for {symbol}: {e}", exc_info=True) # Add traceback
            continue

    logger.error(f"Failed to fetch price series for {symbol} from all sources: {source_preference}")
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

# --- Added missing fetch functions ---

async def fetch_insider_trades(symbol: str):
    """
    Fetch insider trading data for a given symbol.

    Args:
        symbol: Ticker symbol to fetch insider trades for.

    Returns:
        List of dictionaries with insider trading data.
    """
    # Assuming UnifiedDataProvider will have a method like fetch_fundamental_data or similar
    return await provider.fetch_data_resilient(symbol, "insider_trades")

async def fetch_corporate_actions(symbol: str):
    """
    Fetch corporate actions (dividends, splits, etc.) for a given symbol.

    Args:
        symbol: Ticker symbol to fetch corporate actions for.

    Returns:
        List of dictionaries with corporate action data.
    """
    return await provider.fetch_data_resilient(symbol, "corporate_actions")

async def fetch_earnings_calendar(symbol: str):
    """
    Fetch earnings calendar data for a given symbol.

    Args:
        symbol: Ticker symbol to fetch earnings dates for.

    Returns:
        Dictionary with upcoming or historical earnings dates.
    """
    return await provider.fetch_data_resilient(symbol, "earnings_calendar")

async def fetch_management_info(symbol: str):
    """
    Fetch management and executive information for a given symbol.

    Args:
        symbol: Ticker symbol to fetch management info for.

    Returns:
        Dictionary with management information.
    """
    # This might be part of fetch_company_info or require a specific endpoint
    return await provider.fetch_data_resilient(symbol, "management_info")

async def fetch_market_regime_data(symbol: str = None):
    """
    Fetch market regime data (e.g., volatility, trend).
    Can be general market or specific to a symbol if supported.

    Args:
        symbol: Optional ticker symbol. If None, fetches general market regime.

    Returns:
        Dictionary with market regime indicators.
    """
    target = symbol if symbol else "market"
    return await provider.fetch_data_resilient(target, "market_regime")

async def fetch_news_sentiment(symbol: str):
    """
    Fetch news sentiment data for a given symbol.

    Args:
        symbol: Ticker symbol to fetch news sentiment for.

    Returns:
        Dictionary or score representing news sentiment.
    """
    return await provider.fetch_data_resilient(symbol, "news_sentiment")

async def fetch_wacc(symbol: str):
    """
    Fetch or calculate the Weighted Average Cost of Capital (WACC) for a given symbol.

    Args:
        symbol: Ticker symbol to fetch WACC for.

    Returns:
        Dictionary or float representing WACC.
    """
    # Calculation might be complex, provider might fetch components or pre-calculated value
    return await provider.fetch_data_resilient(symbol, "wacc")

# --- End of added functions ---

async def fetch_company_info(symbol: str, data_type: str = None):
    """
    Fetch company information (overview) for a given symbol.

    Args:
        symbol: Ticker symbol to fetch company info for.
        data_type: Optional specific piece of info (e.g., 'eps', 'beta'). Provider handles this.

    Returns:
        Dictionary with company information.
    """
    # UnifiedDataProvider handles fetching specific parts if data_type is provided
    return await provider.fetch_company_info(symbol)

async def fetch_cash_flow_data(symbol: str):
    """
    Fetch cash flow statement data for a given symbol.

    Args:
        symbol: Ticker symbol to fetch cash flow data for.

    Returns:
        DataFrame or Dictionary with cash flow data.
    """
    # Assuming provider.fetch_historical_data can fetch fundamentals like cashflow
    # We might need start/end dates, but let's try fetching the latest available first.
    # The exact implementation might depend on the UnifiedDataProvider's capabilities.
    # For now, let's assume it fetches the latest annual cash flow.
    # A more robust implementation might require specific date handling.
    return await provider.fetch_historical_data(symbol, "cashflow")

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

# --- Added missing fetch functions for ImportErrors ---

async def fetch_volume_series(symbol: str, start_date: str = None, end_date: str = None):
    """Placeholder: Fetch volume series data."""
    logger.warning(f"fetch_volume_series not implemented for {symbol}")
    # In a real implementation, fetch data using provider
    # Example: return await provider.fetch_price_data(symbol, start_date, end_date, interval='1d')
    # Returning None or empty DataFrame for now
    import pandas as pd
    return pd.DataFrame({'volume': []})

async def fetch_interest_rate(country: str = 'US'):
    """Placeholder: Fetch interest rate data."""
    logger.warning(f"fetch_interest_rate not implemented for {country}")
    # Example: return await provider.fetch_macro_data('interest_rate', country)
    return None

async def fetch_inflation_rate(country: str = 'US'):
    """Placeholder: Fetch inflation rate data."""
    logger.warning(f"fetch_inflation_rate not implemented for {country}")
    # Example: return await provider.fetch_macro_data('inflation_rate', country)
    return None

async def fetch_gdp_growth(country: str = 'US'):
    """Placeholder: Fetch GDP growth data."""
    logger.warning(f"fetch_gdp_growth not implemented for {country}")
    # Example: return await provider.fetch_macro_data('gdp_growth', country)
    return None

# --- End of added placeholder functions ---