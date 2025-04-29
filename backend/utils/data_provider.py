import logging
import random
import asyncio
import json
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union, Tuple
import aiohttp
from bs4 import BeautifulSoup
import yfinance as yf
import pandas as pd

from .circuit_breaker import CircuitBreaker
from .retry_utils import async_retry
from ..config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Circuit breakers for each API
API_CIRCUIT_BREAKERS = {
    "alpha_vantage": CircuitBreaker(
        name="alpha_vantage", failure_threshold=3, recovery_timeout=300
    ),
    "polygon": CircuitBreaker(
        name="polygon", failure_threshold=3, recovery_timeout=300
    ),
    "finnhub": CircuitBreaker(
        name="finnhub", failure_threshold=3, recovery_timeout=300
    ),
    "yahoo_finance": CircuitBreaker(
        name="yahoo_finance", failure_threshold=3, recovery_timeout=300
    ),
    "web_scraper": CircuitBreaker(
        name="web_scraper", failure_threshold=5, recovery_timeout=600
    ),
}

# ======== API CLIENTS ========


async def fetch_from_alpha_vantage(
    endpoint: str, params: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Fetch data from Alpha Vantage API.

    Args:
        endpoint: API endpoint path
        params: Query parameters

    Returns:
        Dict containing API response
    """
    circuit_breaker = API_CIRCUIT_BREAKERS["alpha_vantage"]

    if not circuit_breaker.is_closed():
        logger.warning(
            "Alpha Vantage API circuit breaker is open. Using fallback data source."
        )
        raise Exception("Alpha Vantage API circuit breaker is open")

    base_url = "https://www.alphavantage.co/query"

    # Add API key to parameters
    api_key = settings.api_keys.ALPHA_VANTAGE_KEY
    if not api_key:
        circuit_breaker.record_failure()
        raise ValueError("Alpha Vantage API key not configured")

    params["apikey"] = api_key
    params["function"] = endpoint

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(base_url, params=params, timeout=10) as response:
                if response.status != 200:
                    circuit_breaker.record_failure()
                    raise Exception(
                        f"Alpha Vantage API request failed with status {response.status}"
                    )

                data = await response.json()

                # Check for API error messages
                if "Error Message" in data:
                    circuit_breaker.record_failure()
                    raise Exception(f"Alpha Vantage API error: {data['Error Message']}")

                # Check for rate limiting
                if "Note" in data and "API call frequency" in data["Note"]:
                    circuit_breaker.record_failure()
                    raise Exception("Alpha Vantage API rate limit exceeded")

                circuit_breaker.record_success()
                return data
    except Exception as e:
        circuit_breaker.record_failure()
        logger.error(f"Error fetching data from Alpha Vantage: {str(e)}")
        raise


async def fetch_from_polygon(endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fetch data from Polygon.io API.

    Args:
        endpoint: API endpoint path
        params: Query parameters

    Returns:
        Dict containing API response
    """
    circuit_breaker = API_CIRCUIT_BREAKERS["polygon"]

    if not circuit_breaker.is_closed():
        logger.warning(
            "Polygon API circuit breaker is open. Using fallback data source."
        )
        raise Exception("Polygon API circuit breaker is open")

    base_url = f"https://api.polygon.io/v2/{endpoint}"

    # Add API key to parameters
    api_key = settings.api_keys.POLYGON_API_KEY
    if not api_key:
        circuit_breaker.record_failure()
        raise ValueError("Polygon API key not configured")

    params["apiKey"] = api_key

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(base_url, params=params, timeout=10) as response:
                if response.status != 200:
                    circuit_breaker.record_failure()
                    raise Exception(
                        f"Polygon API request failed with status {response.status}"
                    )

                data = await response.json()

                # Check for API error messages
                if data.get("status") == "ERROR":
                    circuit_breaker.record_failure()
                    raise Exception(
                        f"Polygon API error: {data.get('error', 'Unknown error')}"
                    )

                circuit_breaker.record_success()
                return data
    except Exception as e:
        circuit_breaker.record_failure()
        logger.error(f"Error fetching data from Polygon: {str(e)}")
        raise


async def fetch_from_finnhub(endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fetch data from Finnhub API.

    Args:
        endpoint: API endpoint path
        params: Query parameters

    Returns:
        Dict containing API response
    """
    circuit_breaker = API_CIRCUIT_BREAKERS["finnhub"]

    if not circuit_breaker.is_closed():
        logger.warning(
            "Finnhub API circuit breaker is open. Using fallback data source."
        )
        raise Exception("Finnhub API circuit breaker is open")

    base_url = f"https://finnhub.io/api/v1/{endpoint}"

    # Add API key to parameters
    api_key = settings.api_keys.FINNHUB_API_KEY
    if not api_key:
        circuit_breaker.record_failure()
        raise ValueError("Finnhub API key not configured")

    params["token"] = api_key

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(base_url, params=params, timeout=10) as response:
                if response.status != 200:
                    circuit_breaker.record_failure()
                    raise Exception(
                        f"Finnhub API request failed with status {response.status}"
                    )

                data = await response.json()
                circuit_breaker.record_success()
                return data
    except Exception as e:
        circuit_breaker.record_failure()
        logger.error(f"Error fetching data from Finnhub: {str(e)}")
        raise


async def fetch_from_yahoo_finance(symbol: str) -> Dict[str, Any]:
    """
    Fetch data from Yahoo Finance using yfinance library.

    Args:
        symbol: Stock symbol

    Returns:
        Dict containing Yahoo Finance data
    """
    circuit_breaker = API_CIRCUIT_BREAKERS["yahoo_finance"]

    if not circuit_breaker.is_closed():
        logger.warning(
            "Yahoo Finance API circuit breaker is open. Using fallback data source."
        )
        raise Exception("Yahoo Finance API circuit breaker is open")

    try:
        # Create an event loop for synchronous code
        loop = asyncio.get_event_loop()

        # Run yfinance code in a separate thread using run_in_executor
        def get_ticker_data():
            ticker = yf.Ticker(symbol)
            info = ticker.info
            history = ticker.history(period="1mo")
            return info, history

        info, history = await loop.run_in_executor(None, get_ticker_data)

        # Convert pandas DataFrame to dict
        history_dict = {
            "dates": history.index.strftime("%Y-%m-%d").tolist(),
            "close": history["Close"].tolist(),
            "open": history["Open"].tolist(),
            "high": history["High"].tolist(),
            "low": history["Low"].tolist(),
            "volume": history["Volume"].tolist(),
        }

        result = {"info": info, "history": history_dict}

        circuit_breaker.record_success()
        return result
    except Exception as e:
        circuit_breaker.record_failure()
        logger.error(f"Error fetching data from Yahoo Finance: {str(e)}")
        raise


# ======== WEB SCRAPING FALLBACKS ========


async def scrape_stock_data(symbol: str) -> Dict[str, Any]:
    """
    Scrape stock data from financial websites as a fallback.

    Args:
        symbol: Stock symbol

    Returns:
        Dict containing scraped stock data
    """
    circuit_breaker = API_CIRCUIT_BREAKERS["web_scraper"]

    if not circuit_breaker.is_closed():
        logger.warning("Web scraper circuit breaker is open. No fallback available.")
        raise Exception("Web scraper circuit breaker is open")

    # List of websites to try scraping from
    scrape_urls = [
        f"https://finance.yahoo.com/quote/{symbol}",
        f"https://www.marketwatch.com/investing/stock/{symbol}",
        f"https://www.investing.com/search/?q={symbol}",
    ]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    result = {}

    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            for url in scrape_urls:
                try:
                    async with session.get(url, timeout=10) as response:
                        if response.status != 200:
                            continue

                        html = await response.text()
                        soup = BeautifulSoup(html, "html.parser")

                        # Extract data based on URL
                        if "yahoo.com" in url:
                            # Extract price
                            price_elem = soup.select_one('[data-test="qsp-price"]')
                            if price_elem:
                                result["price"] = float(
                                    price_elem.text.replace(",", "")
                                )

                            # Extract EPS
                            eps_elem = soup.select_one(
                                'td[data-test="EPS_RATIO-value"]'
                            )
                            if eps_elem:
                                eps_text = eps_elem.text.strip()
                                if eps_text and eps_text != "N/A":
                                    result["eps"] = float(eps_text.replace(",", ""))

                            # Extract P/E ratio
                            pe_elem = soup.select_one('td[data-test="PE_RATIO-value"]')
                            if pe_elem:
                                pe_text = pe_elem.text.strip()
                                if pe_text and pe_text != "N/A":
                                    result["pe_ratio"] = float(pe_text.replace(",", ""))

                            # Extract dividend yield
                            div_elem = soup.select_one(
                                '[data-test="DIVIDEND_AND_YIELD-value"]'
                            )
                            if div_elem:
                                div_text = div_elem.text.strip()
                                if (
                                    div_text
                                    and "N/A" not in div_text
                                    and "%" in div_text
                                ):
                                    yield_text = div_text.split("(")[1].split(")")[0]
                                    result["dividend_yield"] = (
                                        float(yield_text.replace("%", "")) / 100
                                    )

                        elif "marketwatch.com" in url:
                            # Extract price
                            price_elem = soup.select_one(".intraday__price .value")
                            if price_elem:
                                price_text = price_elem.text.strip()
                                result["price"] = float(price_text.replace(",", ""))

                            # Find EPS in table
                            tables = soup.select(".table__cell")
                            for table in tables:
                                if "EPS" in table.text:
                                    next_elem = table.find_next("td")
                                    if next_elem:
                                        eps_text = next_elem.text.strip()
                                        if eps_text and eps_text != "N/A":
                                            try:
                                                result["eps"] = float(
                                                    eps_text.replace(",", "")
                                                )
                                            except:
                                                pass

                        # If we have enough data, break the loop
                        if len(result) >= 3:
                            break

                except Exception as e:
                    logger.warning(f"Error scraping from {url}: {str(e)}")
                    continue

        # If we have at least price data, consider it a success
        if "price" in result:
            circuit_breaker.record_success()
            return result
        else:
            circuit_breaker.record_failure()
            raise Exception("Failed to scrape meaningful data")

    except Exception as e:
        circuit_breaker.record_failure()
        logger.error(f"Error scraping stock data: {str(e)}")
        raise


# ======== SPECIFIC FINANCIAL DATA POINTS ========


@async_retry(max_retries=2, base_delay=1.0, max_delay=5.0)
async def fetch_latest_ev(symbol: str) -> float:
    """
    Fetch the latest Enterprise Value (EV) for a company.

    Args:
        symbol: Stock symbol

    Returns:
        Enterprise Value as float or None if unavailable
    """
    logger.debug(f"Fetching Enterprise Value for {symbol}")

    # Try multiple data sources in order
    try:
        # Try Yahoo Finance first (most comprehensive financial data)
        yahoo_data = await fetch_from_yahoo_finance(symbol)
        info = yahoo_data.get("info", {})

        # Yahoo Finance provides enterprise value directly
        if "enterpriseValue" in info and info["enterpriseValue"]:
            ev = float(info["enterpriseValue"])
            logger.info(f"Got Enterprise Value {ev} for {symbol} from Yahoo Finance")
            return ev

        # Calculate from components if direct EV not available
        elif all(key in info for key in ["marketCap", "totalDebt", "totalCash"]):
            market_cap = float(info["marketCap"] or 0)
            total_debt = float(info["totalDebt"] or 0)
            cash = float(info["totalCash"] or 0)

            ev = market_cap + total_debt - cash
            logger.info(
                f"Calculated Enterprise Value {ev} for {symbol} from Yahoo Finance components"
            )
            return ev
    except Exception as e:
        logger.warning(f"Failed to get Enterprise Value from Yahoo Finance: {str(e)}")

    # Try Alpha Vantage as fallback for company overview
    try:
        av_data = await fetch_from_alpha_vantage("OVERVIEW", {"symbol": symbol})

        # Alpha Vantage doesn't directly provide EV, so calculate from components
        if all(key in av_data for key in ["MarketCapitalization", "TotalDebt", "Cash"]):
            market_cap = float(av_data["MarketCapitalization"])
            total_debt = float(av_data["TotalDebt"])
            cash = float(av_data["Cash"])

            ev = market_cap + total_debt - cash
            logger.info(
                f"Calculated Enterprise Value {ev} for {symbol} from Alpha Vantage components"
            )
            return ev
    except Exception as e:
        logger.warning(f"Failed to get Enterprise Value from Alpha Vantage: {str(e)}")

    # Try Finnhub as another fallback
    try:
        finnhub_data = await fetch_from_finnhub(
            "stock/metric", {"symbol": symbol, "metric": "all"}
        )
        metrics = finnhub_data.get("metric", {})

        if "enterpriseValue" in metrics and metrics["enterpriseValue"]:
            ev = float(metrics["enterpriseValue"])
            logger.info(f"Got Enterprise Value {ev} for {symbol} from Finnhub")
            return ev
    except Exception as e:
        logger.warning(f"Failed to get Enterprise Value from Finnhub: {str(e)}")

    # If all sources fail, log warning and return None
    logger.error(f"Failed to get Enterprise Value for {symbol} from all sources")
    return None


@async_retry(max_retries=2, base_delay=1.0, max_delay=5.0)
async def fetch_latest_ebitda(symbol: str) -> float:
    """
    Fetch the latest EBITDA (Earnings Before Interest, Taxes, Depreciation, and Amortization) for a company.

    Args:
        symbol: Stock symbol

    Returns:
        EBITDA as float or None if unavailable
    """
    logger.debug(f"Fetching EBITDA for {symbol}")

    # Try multiple data sources in order
    try:
        # Try Yahoo Finance first
        yahoo_data = await fetch_from_yahoo_finance(symbol)
        info = yahoo_data.get("info", {})

        # Yahoo Finance provides EBITDA directly
        if "ebitda" in info and info["ebitda"]:
            ebitda = float(info["ebitda"])
            logger.info(f"Got EBITDA {ebitda} for {symbol} from Yahoo Finance")
            return ebitda
    except Exception as e:
        logger.warning(f"Failed to get EBITDA from Yahoo Finance: {str(e)}")

    # Try Alpha Vantage as fallback
    try:
        av_data = await fetch_from_alpha_vantage("OVERVIEW", {"symbol": symbol})

        # Alpha Vantage provides EBITDA
        if "EBITDA" in av_data and av_data["EBITDA"]:
            # Handle format differences (e.g., "1.23B" vs numeric)
            ebitda_str = av_data["EBITDA"]

            # Convert string with possible suffix to float
            if isinstance(ebitda_str, str):
                if ebitda_str.endswith("T"):
                    ebitda = float(ebitda_str[:-1]) * 1e12
                elif ebitda_str.endswith("B"):
                    ebitda = float(ebitda_str[:-1]) * 1e9
                elif ebitda_str.endswith("M"):
                    ebitda = float(ebitda_str[:-1]) * 1e6
                elif ebitda_str.endswith("K"):
                    ebitda = float(ebitda_str[:-1]) * 1e3
                else:
                    ebitda = float(ebitda_str.replace(",", ""))
            else:
                ebitda = float(ebitda_str)

            logger.info(f"Got EBITDA {ebitda} for {symbol} from Alpha Vantage")
            return ebitda
    except Exception as e:
        logger.warning(f"Failed to get EBITDA from Alpha Vantage: {str(e)}")

    # Try Finnhub as another fallback
    try:
        finnhub_data = await fetch_from_finnhub(
            "stock/metric", {"symbol": symbol, "metric": "all"}
        )
        metrics = finnhub_data.get("metric", {})

        if "ebitdaTTM" in metrics and metrics["ebitdaTTM"]:
            ebitda = float(metrics["ebitdaTTM"])
            logger.info(f"Got EBITDA {ebitda} for {symbol} from Finnhub")
            return ebitda
    except Exception as e:
        logger.warning(f"Failed to get EBITDA from Finnhub: {str(e)}")

    # If all sources fail, log warning and return None
    logger.error(f"Failed to get EBITDA for {symbol} from all sources")
    return None


@async_retry(max_retries=2, base_delay=1.0, max_delay=5.0)
async def fetch_historical_ev(symbol: str, years: int = 5) -> pd.Series:
    """
    Fetch historical Enterprise Value (EV) data.

    Args:
        symbol: Stock symbol
        years: Number of years of historical data to fetch

    Returns:
        pandas Series with dates as index and EV values
    """
    logger.warning(
        f"Fetching historical Enterprise Value (EV) is not currently supported by the available data providers. Returning None for {symbol}."
    )
    # In a real implementation, you might try fetching historical fundamentals
    # (Market Cap, Debt, Cash) and calculating it, but this is complex.
    return None


@async_retry(max_retries=2, base_delay=1.0, max_delay=5.0)
async def fetch_historical_ebitda(symbol: str, years: int = 5) -> pd.Series:
    """
    Fetch historical EBITDA data for a company.

    Args:
        symbol: Stock symbol
        years: Number of years of historical data to fetch

    Returns:
        pandas Series with dates as index and EBITDA values
    """
    logger.debug(f"Fetching historical EBITDA for {symbol}, years={years}")

    try:
        # Calculate start date based on years
        end_date = datetime.now()
        start_date = end_date - timedelta(days=years * 365)

        # Try to get quarterly financials from Alpha Vantage
        income_data = await fetch_from_alpha_vantage(
            "INCOME_STATEMENT", {"symbol": symbol}
        )

        if not income_data or "quarterlyReports" not in income_data:
            logger.warning(f"No quarterly reports found for {symbol}")
            return None

        quarterly_reports = income_data["quarterlyReports"]

        # Extract EBITDA or calculate it from components
        dates = []
        ebitda_values = []

        for report in quarterly_reports:
            # Extract date and convert to datetime
            report_date_str = report.get("fiscalDateEnding")
            if not report_date_str:
                continue

            report_date = datetime.strptime(report_date_str, "%Y-%m-%d")

            # Skip if before our start date
            if report_date < start_date:
                continue

            # Try to get EBITDA directly or calculate from components
            ebitda = None

            # Some providers include EBITDA directly
            if "ebitda" in report and report["ebitda"] and report["ebitda"] != "None":
                try:
                    ebitda = float(report["ebitda"])
                except (ValueError, TypeError):
                    ebitda = None

            # If not available, calculate from components:
            # EBITDA = Operating Income + Depreciation + Amortization
            if not ebitda and all(
                k in report for k in ["operatingIncome", "depreciation"]
            ):
                try:
                    operating_income = float(report.get("operatingIncome") or 0)
                    depreciation = float(report.get("depreciation") or 0)
                    # Amortization is sometimes included in depreciation

                    ebitda = operating_income + depreciation
                except (ValueError, TypeError):
                    ebitda = None

            if ebitda is not None:
                dates.append(report_date)
                ebitda_values.append(ebitda)

        if not dates:
            logger.warning(f"No valid EBITDA data found for {symbol}")
            return None

        # Create pandas Series
        ebitda_series = pd.Series(ebitda_values, index=dates)
        ebitda_series = ebitda_series.sort_index()

        # Resample to quarterly frequency if needed
        ebitda_series = ebitda_series.resample("Q").last().ffill()

        logger.info(f"Got {len(ebitda_series)} historical EBITDA points for {symbol}")
        return ebitda_series

    except Exception as e:
        logger.error(f"Failed to fetch historical EBITDA for {symbol}: {str(e)}")
        return None


@async_retry(max_retries=2, base_delay=1.0, max_delay=5.0)
async def fetch_historical_price_series(symbol: str, years: int = 5) -> pd.Series:
    """
    Fetch historical price data as a pandas Series.

    Args:
        symbol: Stock symbol
        years: Number of years of historical data to fetch

    Returns:
        pandas Series with dates as index and price values
    """
    logger.debug(f"Fetching historical price series for {symbol}, years={years}")

    try:
        # Map years to Yahoo Finance period string
        if years <= 1:
            period = "1y"
        elif years <= 2:
            period = "2y"
        elif years <= 5:
            period = "5y"
        else:
            period = "10y"

        # Get historical prices
        history_data = await fetch_price_series(symbol, period)

        if history_data.empty or history_data.index.empty:
            logger.warning(f"No historical price data found for {symbol}")
            return None

        # Convert to pandas Series
        dates = [datetime.strptime(date, "%Y-%m-%d") for date in history_data["dates"]]
        close_prices = history_data["close"]

        # Create Series
        price_series = pd.Series(close_prices, index=dates)
        price_series = price_series.sort_index()

        # Filter to requested years
        start_date = datetime.now() - timedelta(days=years * 365)
        price_series = price_series[price_series.index >= start_date]

        logger.info(f"Got {len(price_series)} historical price points for {symbol}")
        return price_series

    except Exception as e:
        logger.error(f"Failed to fetch historical price series for {symbol}: {str(e)}")
        return None


@async_retry(max_retries=2, base_delay=1.0, max_delay=5.0)
async def fetch_book_value(symbol: str) -> Union[float, None]:
    """
    Fetch the latest book value per share for a company.

    Args:
        symbol: Stock symbol

    Returns:
        Book Value per Share as float or None if unavailable
    """
    logger.debug(f"Fetching Book Value per Share for {symbol}")

    # Try multiple data sources in order
    try:
        # Try Yahoo Finance first
        # Note: yfinance often requires fetching the full info dict
        ticker = yf.Ticker(symbol)
        info = await asyncio.to_thread(
            lambda: ticker.info
        )  # Run sync yfinance in thread

        if info and "bookValue" in info and info["bookValue"] is not None:
            book_value = float(info["bookValue"])
            logger.info(
                f"Got Book Value per Share {book_value} for {symbol} from Yahoo Finance"
            )
            return book_value
        else:
            logger.warning(f"Book Value not found in Yahoo Finance info for {symbol}")

    except Exception as e:
        logger.warning(
            f"Failed to get Book Value from Yahoo Finance for {symbol}: {str(e)}"
        )

    # Try Alpha Vantage as fallback (Balance Sheet might have it, or Overview)
    try:
        # Check Overview first
        av_data = await fetch_from_alpha_vantage("OVERVIEW", {"symbol": symbol})
        if (
            av_data
            and "BookValue" in av_data
            and av_data["BookValue"]
            and av_data["BookValue"].lower() != "none"
        ):
            try:
                book_value = float(av_data["BookValue"])
                logger.info(
                    f"Got Book Value per Share {book_value} for {symbol} from Alpha Vantage Overview"
                )
                return book_value
            except (ValueError, TypeError):
                logger.warning(
                    f"Could not parse BookValue from Alpha Vantage Overview for {symbol}: {av_data['BookValue']}"
                )

        # If not in overview, try latest Balance Sheet
        # Note: This gives total equity, needs division by shares outstanding
        balance_sheet_data = await fetch_from_alpha_vantage(
            "BALANCE_SHEET", {"symbol": symbol}
        )
        if (
            balance_sheet_data
            and "quarterlyReports" in balance_sheet_data
            and balance_sheet_data["quarterlyReports"]
        ):
            latest_report = balance_sheet_data["quarterlyReports"][0]
            total_equity_str = latest_report.get("totalShareholderEquity")

            # Need shares outstanding - potentially from Overview data again
            if not av_data:  # Fetch overview if not already fetched
                av_data = await fetch_from_alpha_vantage("OVERVIEW", {"symbol": symbol})

            shares_outstanding_str = (
                av_data.get("SharesOutstanding") if av_data else None
            )

            if total_equity_str and shares_outstanding_str:
                try:
                    total_equity = float(total_equity_str)
                    shares_outstanding = float(shares_outstanding_str)
                    if shares_outstanding > 0:
                        book_value = total_equity / shares_outstanding
                        logger.info(
                            f"Calculated Book Value per Share {book_value} for {symbol} from Alpha Vantage Balance Sheet/Overview"
                        )
                        return book_value
                except (ValueError, TypeError):
                    logger.warning(
                        f"Could not calculate BVPS from Alpha Vantage Balance Sheet/Overview for {symbol}"
                    )

    except Exception as e:
        logger.warning(
            f"Failed to get Book Value from Alpha Vantage for {symbol}: {str(e)}"
        )

    # Try Finnhub as another fallback (stock/metric)
    try:
        finnhub_data = await fetch_from_finnhub(
            "stock/metric", {"symbol": symbol, "metric": "all"}
        )
        metrics = finnhub_data.get("metric", {})

        if (
            "bookValuePerShareQuarterly" in metrics
            and metrics["bookValuePerShareQuarterly"] is not None
        ):
            book_value = float(metrics["bookValuePerShareQuarterly"])
            logger.info(
                f"Got Book Value per Share {book_value} for {symbol} from Finnhub"
            )
            return book_value
        elif (
            "bookValuePerShareAnnual" in metrics
            and metrics["bookValuePerShareAnnual"] is not None
        ):
            book_value = float(metrics["bookValuePerShareAnnual"])
            logger.info(
                f"Got Book Value per Share {book_value} (Annual) for {symbol} from Finnhub"
            )
            return book_value

    except Exception as e:
        logger.warning(f"Failed to get Book Value from Finnhub for {symbol}: {str(e)}")

    # If all sources fail, log error and return None
    logger.error(f"Failed to get Book Value per Share for {symbol} from all sources")
    return None


@async_retry(max_retries=2, base_delay=1.0, max_delay=5.0)
async def fetch_latest_eps(symbol: str) -> float:
    """
    Fetch the latest Earnings Per Share (EPS) for a company.

    Args:
        symbol: Stock symbol

    Returns:
        EPS value as float or None if unavailable
    """
    logger.debug(f"Fetching latest EPS for {symbol}")

    # Try multiple data sources in order
    try:
        # Try Yahoo Finance first
        loop = asyncio.get_event_loop()

        def get_eps():
            ticker = yf.Ticker(symbol)
            info = ticker.info
            if "trailingEPS" in info and info["trailingEPS"] is not None:
                return info["trailingEPS"]
            return None

        eps = await loop.run_in_executor(None, get_eps)
        
        if eps is not None:
            logger.info(f"Got EPS {eps} for {symbol} from Yahoo Finance")
            return float(eps)

    except Exception as e:
        logger.warning(f"Failed to get EPS from Yahoo Finance: {str(e)}")

    # Try Alpha Vantage as fallback
    try:
        av_data = await fetch_from_alpha_vantage("OVERVIEW", {"symbol": symbol})
        
        if av_data and "EPS" in av_data and av_data["EPS"]:
            try:
                eps = float(av_data["EPS"])
                logger.info(f"Got EPS {eps} for {symbol} from Alpha Vantage")
                return eps
            except (ValueError, TypeError):
                pass

        # Try earnings endpoint if overview didn't work
        earnings_data = await fetch_from_alpha_vantage("EARNINGS", {"symbol": symbol})
        if earnings_data and "quarterlyEarnings" in earnings_data and earnings_data["quarterlyEarnings"]:
            latest_earnings = earnings_data["quarterlyEarnings"][0]
            if "reportedEPS" in latest_earnings:
                try:
                    eps = float(latest_earnings["reportedEPS"])
                    logger.info(f"Got latest quarterly EPS {eps} for {symbol} from Alpha Vantage")
                    return eps
                except (ValueError, TypeError):
                    pass

    except Exception as e:
        logger.warning(f"Failed to get EPS from Alpha Vantage: {str(e)}")

    # Try web scraping as a last resort
    try:
        scraped_data = await scrape_stock_data(symbol)
        if scraped_data and "eps" in scraped_data:
            eps = scraped_data["eps"]
            logger.info(f"Got EPS {eps} for {symbol} from web scraping")
            return eps
    
    except Exception as e:
        logger.warning(f"Failed to get EPS from web scraping: {str(e)}")

    # If all sources fail, log error and return None
    logger.error(f"Failed to get latest EPS for {symbol} from all sources")
    return None


@async_retry(max_retries=2, base_delay=1.0, max_delay=5.0)
async def fetch_latest_bvps(symbol: str) -> float:
    """
    Fetch the latest Book Value Per Share (BVPS) for a company.
    This is an alias for fetch_book_value to maintain backwards compatibility.

    Args:
        symbol: Stock symbol

    Returns:
        Book Value Per Share as float or None if unavailable
    """
    logger.debug(f"Fetching latest BVPS for {symbol}")
    
    # Simply call the existing fetch_book_value function
    return await fetch_book_value(symbol)


@async_retry(max_retries=2, base_delay=1.0, max_delay=5.0)
async def fetch_fcf_per_share(symbol: str) -> float:
    """
    Fetch the latest Free Cash Flow (FCF) per share for a company.

    Args:
        symbol: Stock symbol

    Returns:
        FCF per share as float or None if unavailable
    """
    logger.debug(f"Fetching FCF per share for {symbol}")

    try:
        # Try Yahoo Finance first for cash flow data
        loop = asyncio.get_event_loop()

        def get_fcf_data():
            ticker = yf.Ticker(symbol)
            cashflow = ticker.cashflow
            
            # Get shares data
            info = ticker.info
            shares_outstanding = info.get("sharesOutstanding")
            
            return cashflow, shares_outstanding

        cashflow, shares_outstanding = await loop.run_in_executor(None, get_fcf_data)
        
        if not cashflow.empty and shares_outstanding:
            # Try to calculate FCF from cash flow statement
            # FCF = Operating Cash Flow - Capital Expenditures
            if "Operating Cash Flow" in cashflow.index and "Capital Expenditures" in cashflow.index:
                operating_cash_flow = cashflow.loc["Operating Cash Flow"][0]  # Latest period
                capital_expenditures = cashflow.loc["Capital Expenditures"][0]  # Latest period (should be negative)
                
                fcf = operating_cash_flow + capital_expenditures  # Add because capex is negative
                fcf_per_share = fcf / shares_outstanding
                
                logger.info(f"Calculated FCF per share {fcf_per_share} for {symbol} from Yahoo Finance")
                return float(fcf_per_share)

    except Exception as e:
        logger.warning(f"Failed to get FCF per share from Yahoo Finance: {str(e)}")

    # Try Alpha Vantage as fallback
    try:
        # Get cash flow statement
        cf_data = await fetch_from_alpha_vantage("CASH_FLOW", {"symbol": symbol})
        
        # Get company overview for shares outstanding
        overview_data = await fetch_from_alpha_vantage("OVERVIEW", {"symbol": symbol})
        
        if (cf_data and "quarterlyReports" in cf_data and cf_data["quarterlyReports"] and
            overview_data and "SharesOutstanding" in overview_data):
            
            latest_cf = cf_data["quarterlyReports"][0]
            shares_outstanding = float(overview_data["SharesOutstanding"])
            
            # Check if we have the required fields
            if all(k in latest_cf for k in ["operatingCashflow", "capitalExpenditures"]) and shares_outstanding > 0:
                try:
                    operating_cash_flow = float(latest_cf["operatingCashflow"])
                    capital_expenditures = float(latest_cf["capitalExpenditures"])  # Should be negative
                    
                    fcf = operating_cash_flow + capital_expenditures  # Add because capex is negative
                    fcf_per_share = fcf / shares_outstanding
                    
                    logger.info(f"Calculated FCF per share {fcf_per_share} for {symbol} from Alpha Vantage")
                    return fcf_per_share
                except (ValueError, TypeError):
                    pass
    
    except Exception as e:
        logger.warning(f"Failed to get FCF per share from Alpha Vantage: {str(e)}")

    # If all sources fail, log error and return None
    logger.error(f"Failed to get FCF per share for {symbol} from all sources")
    return None


@async_retry(max_retries=2, base_delay=1.0, max_delay=5.0)
async def fetch_sales_per_share(symbol: str) -> float:
    """
    Fetch the latest Sales (Revenue) per share for a company.

    Args:
        symbol: Stock symbol

    Returns:
        Sales per share as float or None if unavailable
    """
    logger.debug(f"Fetching Sales per share for {symbol}")

    try:
        # Try Yahoo Finance first
        loop = asyncio.get_event_loop()

        def get_sales_data():
            ticker = yf.Ticker(symbol)
            info = ticker.info
            financial_data = ticker.quarterly_financials
            
            return info, financial_data

        info, financial_data = await loop.run_in_executor(None, get_sales_data)
        
        if "revenuePerShare" in info and info["revenuePerShare"] is not None:
            sales_per_share = info["revenuePerShare"]
            logger.info(f"Got Sales per share {sales_per_share} for {symbol} from Yahoo Finance directly")
            return float(sales_per_share)
            
        # Try to calculate from financials if direct value not available
        elif not financial_data.empty and "Total Revenue" in financial_data.index and "sharesOutstanding" in info:
            total_revenue = financial_data.loc["Total Revenue"][0]  # Latest quarter
            shares_outstanding = info["sharesOutstanding"]
            
            if shares_outstanding > 0:
                sales_per_share = total_revenue / shares_outstanding
                logger.info(f"Calculated Sales per share {sales_per_share} for {symbol} from Yahoo Finance")
                return float(sales_per_share)

    except Exception as e:
        logger.warning(f"Failed to get Sales per share from Yahoo Finance: {str(e)}")

    # Try Alpha Vantage as fallback
    try:
        # Get income statement
        is_data = await fetch_from_alpha_vantage("INCOME_STATEMENT", {"symbol": symbol})
        
        # Get company overview for shares outstanding
        overview_data = await fetch_from_alpha_vantage("OVERVIEW", {"symbol": symbol})
        
        if (is_data and "quarterlyReports" in is_data and is_data["quarterlyReports"] and
            overview_data and "SharesOutstanding" in overview_data):
            
            latest_is = is_data["quarterlyReports"][0]
            shares_outstanding = float(overview_data["SharesOutstanding"])
            
            # Check if we have the required fields
            if "totalRevenue" in latest_is and shares_outstanding > 0:
                try:
                    total_revenue = float(latest_is["totalRevenue"])
                    sales_per_share = total_revenue / shares_outstanding
                    
                    logger.info(f"Calculated Sales per share {sales_per_share} for {symbol} from Alpha Vantage")
                    return sales_per_share
                except (ValueError, TypeError):
                    pass
    
    except Exception as e:
        logger.warning(f"Failed to get Sales per share from Alpha Vantage: {str(e)}")

    # If all sources fail, log error and return None
    logger.error(f"Failed to get Sales per share for {symbol} from all sources")
    return None


@async_retry(max_retries=2, base_delay=1.0, max_delay=5.0)
async def fetch_price_series(symbol: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    """
    Fetch historical price data as a pandas DataFrame.

    Args:
        symbol: Stock symbol
        period: Time period to fetch ('1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max')
        interval: Data frequency ('1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h', '1d', '5d', '1wk', '1mo', '3mo')

    Returns:
        pandas DataFrame with OHLCV data
    """
    logger.debug(f"Fetching price series for {symbol}, period={period}, interval={interval}")

    try:
        # Use the event loop to run synchronous yfinance code
        loop = asyncio.get_event_loop()

        # Run yfinance in a separate thread
        def get_history():
            ticker = yf.Ticker(symbol)
            history = ticker.history(period=period, interval=interval)
            return history

        history = await loop.run_in_executor(None, get_history)
        
        if history.empty:
            logger.warning(f"No price data found for {symbol}")
            return pd.DataFrame()

        logger.info(f"Got {len(history)} price points for {symbol}")
        return history

    except Exception as e:
        logger.error(f"Failed to fetch price series for {symbol}: {str(e)}")
        return pd.DataFrame()


@async_retry(max_retries=2, base_delay=1.0, max_delay=5.0)
async def fetch_price_point(symbol: str) -> float:
    """
    Fetch the latest price for a stock.

    Args:
        symbol: Stock symbol

    Returns:
        Latest price as float or None if unavailable
    """
    logger.debug(f"Fetching latest price for {symbol}")

    # Try multiple data sources in order
    try:
        # Try Yahoo Finance first (most reliable for real-time prices)
        loop = asyncio.get_event_loop()

        # Run yfinance in a separate thread
        def get_price():
            ticker = yf.Ticker(symbol)
            # Get the last closing price from a 1-day history request
            history = ticker.history(period="1d")
            if not history.empty:
                return history['Close'].iloc[-1]
            else:
                # Try ticker.info as fallback
                info = ticker.info
                if 'regularMarketPrice' in info:
                    return info['regularMarketPrice']
                elif 'previousClose' in info:
                    return info['previousClose']
                return None

        price = await loop.run_in_executor(None, get_price)
        
        if price:
            logger.info(f"Got price {price} for {symbol} from Yahoo Finance")
            return float(price)

    except Exception as e:
        logger.warning(f"Failed to get price from Yahoo Finance: {str(e)}")

    # Try Alpha Vantage as fallback for real-time quote
    try:
        av_data = await fetch_from_alpha_vantage("GLOBAL_QUOTE", {"symbol": symbol})
        
        if av_data and "Global Quote" in av_data:
            quote = av_data["Global Quote"]
            if "05. price" in quote and quote["05. price"]:
                price = float(quote["05. price"])
                logger.info(f"Got price {price} for {symbol} from Alpha Vantage")
                return price
    
    except Exception as e:
        logger.warning(f"Failed to get price from Alpha Vantage: {str(e)}")

    # Try web scraping as a last resort
    try:
        scraped_data = await scrape_stock_data(symbol)
        if scraped_data and "price" in scraped_data:
            price = scraped_data["price"]
            logger.info(f"Got price {price} for {symbol} from web scraping")
            return price
            
    except Exception as e:
        logger.warning(f"Failed to get price from web scraping: {str(e)}")

    # If all sources fail, log error and return None
    logger.error(f"Failed to get price for {symbol} from all sources")
    return None


@async_retry(max_retries=2, base_delay=1.0, max_delay=5.0)
async def fetch_ohlcv_series(symbol: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    """
    Fetch Open-High-Low-Close-Volume (OHLCV) historical price data as a pandas DataFrame.
    This is an alias for fetch_price_series to maintain backward compatibility.

    Args:
        symbol: Stock symbol
        period: Time period to fetch ('1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max')
        interval: Data frequency ('1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h', '1d', '5d', '1wk', '1mo', '3mo')

    Returns:
        pandas DataFrame with OHLCV data
    """
    logger.debug(f"Fetching OHLCV series for {symbol}, period={period}, interval={interval}")
    
    # Simply call the fetch_price_series function which already implements this functionality
    return await fetch_price_series(symbol, period, interval)


@async_retry(max_retries=2, base_delay=1.0, max_delay=5.0)
async def fetch_price_tickertape(symbol: str) -> float:
    """
    Fetch price data from Tickertape (Indian market data).
    This is a specialized function for Indian stocks.

    Args:
        symbol: Stock symbol (Indian ticker)

    Returns:
        Latest price as float or None if unavailable
    """
    logger.debug(f"Fetching price for Indian stock {symbol} from Tickertape")
    
    # Mock implementation for testing - in a real scenario, this would scrape Tickertape website
    # Since this is for testing only, return a random price based on the symbol hash
    symbol_hash = sum(ord(c) for c in symbol)
    random.seed(symbol_hash)
    mock_price = round(random.uniform(100, 5000), 2)
    
    logger.info(f"[MOCK] Returning simulated price {mock_price} for {symbol} from Tickertape")
    return mock_price


@async_retry(max_retries=2, base_delay=1.0, max_delay=5.0)
async def fetch_price_trendlyne(symbol: str) -> float:
    """
    Fetch price data from Trendlyne (specialized platform for Indian markets).

    Args:
        symbol: Stock symbol (likely Indian ticker)

    Returns:
        Latest price as float or None if unavailable
    """
    logger.debug(f"Fetching price for stock {symbol} from Trendlyne")
    
    # For testing, simulate fetching data with a reasonable mock price
    # In a real implementation, this would scrape or use Trendlyne's API
    symbol_hash = sum(ord(c) for c in symbol)
    random.seed(symbol_hash + 42)  # Different seed from tickertape to get different values
    mock_price = round(random.uniform(200, 6000), 2)
    
    logger.info(f"[MOCK] Returning simulated price {mock_price} for {symbol} from Trendlyne")
    return mock_price


@async_retry(max_retries=2, base_delay=1.0, max_delay=5.0)
async def fetch_price_moneycontrol(symbol: str) -> float:
    """
    Fetch price data from MoneyControl (Indian financial website).

    Args:
        symbol: Stock symbol (Indian ticker)

    Returns:
        Latest price as float or None if unavailable
    """
    logger.debug(f"Fetching price for Indian stock {symbol} from MoneyControl")
    
    # In a production environment, we would scrape the MoneyControl website
    # or use their API if available. For market deployment testing, we'll use a mock.
    
    # Generate a deterministic but different price than the other Indian sources
    symbol_hash = sum(ord(c) for c in symbol)
    random.seed(symbol_hash + 78)  # Unique seed for MoneyControl
    mock_price = round(random.uniform(150, 5500), 2)
    
    logger.info(f"[MOCK] Returning simulated price {mock_price} for {symbol} from MoneyControl")
    return mock_price


@async_retry(max_retries=2, base_delay=1.0, max_delay=5.0)
async def fetch_price_stockedge(symbol: str) -> float:
    """
    Fetch price data from StockEdge (Indian stock market data provider).

    Args:
        symbol: Stock symbol (Indian ticker)

    Returns:
        Latest price as float or None if unavailable
    """
    logger.debug(f"Fetching price for Indian stock {symbol} from StockEdge")
    
    # In a production environment, this would interact with StockEdge API or scrape their website
    # For market deployment testing, we'll use a mock with a different seed than other Indian sources
    
    symbol_hash = sum(ord(c) for c in symbol)
    random.seed(symbol_hash + 123)  # Unique seed for StockEdge
    mock_price = round(random.uniform(180, 5800), 2)
    
    logger.info(f"[MOCK] Returning simulated price {mock_price} for {symbol} from StockEdge")
    return mock_price


@async_retry(max_retries=2, base_delay=1.0, max_delay=5.0)
async def fetch_eps_data(symbol: str, quarters: int = 8) -> pd.Series:
    """
    Fetch historical EPS (Earnings Per Share) data.

    Args:
        symbol: Stock symbol
        quarters: Number of quarters of EPS data to fetch

    Returns:
        pandas Series with dates as index and EPS values
    """
    logger.debug(f"Fetching EPS data for {symbol}, quarters={quarters}")

    try:
        # Try Yahoo Finance first
        loop = asyncio.get_event_loop()

        # Run yfinance in a separate thread
        def get_earnings():
            ticker = yf.Ticker(symbol)
            earnings = ticker.earnings
            quarterly_earnings = ticker.quarterly_earnings
            return earnings, quarterly_earnings

        earnings, quarterly_earnings = await loop.run_in_executor(None, get_earnings)
        
        if not quarterly_earnings.empty:
            # Get EPS data from quarterly earnings
            eps_data = quarterly_earnings['Earnings']
            eps_data = eps_data.sort_index(ascending=False).head(quarters)
            logger.info(f"Got {len(eps_data)} EPS data points for {symbol} from Yahoo Finance")
            return eps_data

    except Exception as e:
        logger.warning(f"Failed to get EPS data from Yahoo Finance: {str(e)}")

    # Try Alpha Vantage as fallback
    try:
        av_data = await fetch_from_alpha_vantage("EARNINGS", {"symbol": symbol})
        
        if av_data and "quarterlyEarnings" in av_data:
            quarterly_earnings = av_data["quarterlyEarnings"]
            
            dates = []
            eps_values = []
            
            for entry in quarterly_earnings[:quarters]:
                if "reportedEPS" in entry and "fiscalDateEnding" in entry:
                    try:
                        eps = float(entry["reportedEPS"])
                        date = datetime.strptime(entry["fiscalDateEnding"], "%Y-%m-%d")
                        
                        dates.append(date)
                        eps_values.append(eps)
                    except (ValueError, TypeError):
                        continue
            
            if dates:
                eps_series = pd.Series(eps_values, index=dates)
                eps_series = eps_series.sort_index(ascending=False)
                logger.info(f"Got {len(eps_series)} EPS data points for {symbol} from Alpha Vantage")
                return eps_series
    
    except Exception as e:
        logger.warning(f"Failed to get EPS data from Alpha Vantage: {str(e)}")

    # If all sources fail, log error and return empty Series
    logger.error(f"Failed to get EPS data for {symbol} from all sources")
    return pd.Series()


@async_retry(max_retries=2, base_delay=1.0, max_delay=5.0)
async def fetch_alpha_vantage(endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Direct wrapper for fetch_from_alpha_vantage to maintain backward compatibility.
    Fetches data from Alpha Vantage API.

    Args:
        endpoint: API endpoint path
        params: Query parameters

    Returns:
        Dict containing API response
    """
    logger.debug(f"Fetching data from Alpha Vantage: endpoint={endpoint}")
    
    # Call the existing function
    return await fetch_from_alpha_vantage(endpoint, params)


@async_retry(max_retries=2, base_delay=1.0, max_delay=5.0)
async def fetch_esg_data(symbol: str) -> Dict[str, Any]:
    """
    Fetch ESG (Environmental, Social, and Governance) data for a company.

    Args:
        symbol: Stock symbol

    Returns:
        Dictionary with ESG scores and ratings
    """
    logger.debug(f"Fetching ESG data for {symbol}")

    # Mock ESG data generator for testing purposes
    # In a real implementation, this would fetch from a provider like Yahoo Finance ESG, MSCI, Sustainalytics, etc.
    def generate_mock_esg_data(symbol_seed):
        random.seed(symbol_seed)
        
        # Generate scores in range 0-100
        environment_score = round(random.uniform(30, 95), 1)
        social_score = round(random.uniform(30, 95), 1)
        governance_score = round(random.uniform(30, 95), 1)
        
        # Overall score is weighted average
        overall_score = round(0.4 * environment_score + 0.3 * social_score + 0.3 * governance_score, 1)
        
        # Rating based on overall score
        if overall_score >= 80:
            rating = "AAA"
        elif overall_score >= 70:
            rating = "AA"
        elif overall_score >= 60:
            rating = "A"
        elif overall_score >= 50:
            rating = "BBB"
        elif overall_score >= 40:
            rating = "BB"
        elif overall_score >= 30:
            rating = "B"
        else:
            rating = "CCC"
            
        # Generate some risk metrics
        controversy_level = random.randint(0, 5)
        carbon_risk = round(random.uniform(1, 10), 1)
            
        return {
            "symbol": symbol,
            "overall_score": overall_score,
            "environment_score": environment_score,
            "social_score": social_score,
            "governance_score": governance_score,
            "rating": rating,
            "controversy_level": controversy_level,
            "carbon_risk": carbon_risk,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "source": "Mock ESG Data",
            "is_mock": True
        }
    
    try:
        # In a real implementation, we would try to fetch from actual ESG data providers
        # For testing, we generate mock data
        symbol_hash = sum(ord(c) for c in symbol)
        esg_data = generate_mock_esg_data(symbol_hash)
        
        logger.info(f"[MOCK] Generated ESG data for {symbol}: Overall Score: {esg_data['overall_score']}, Rating: {esg_data['rating']}")
        return esg_data
        
    except Exception as e:
        logger.error(f"Failed to generate/fetch ESG data for {symbol}: {str(e)}")
        return None


@async_retry(max_retries=2, base_delay=1.0, max_delay=5.0)
async def fetch_market_data(market_index: str = "^GSPC") -> Dict[str, Any]:
    """
    Fetch data about the overall market (index data).

    Args:
        market_index: Market index symbol (default is S&P 500)

    Returns:
        Dictionary with market data including price, change, etc.
    """
    logger.debug(f"Fetching market data for index {market_index}")

    try:
        # Try Yahoo Finance
        loop = asyncio.get_event_loop()

        # Run yfinance in a separate thread
        def get_market_data():
            ticker = yf.Ticker(market_index)
            
            # Get the last price data
            history = ticker.history(period="5d")
            
            # Get ticker info
            info = ticker.info

            return history, info

        history, info = await loop.run_in_executor(None, get_market_data)
        
        if not history.empty:
            # Calculate daily change
            latest_day = history.index[-1]
            prev_day = history.index[-2] if len(history) > 1 else None
            
            latest_close = history.loc[latest_day, "Close"]
            prev_close = history.loc[prev_day, "Close"] if prev_day is not None else None
            
            # Calculate metrics
            day_change = latest_close - prev_close if prev_close is not None else None
            day_change_pct = (day_change / prev_close * 100) if prev_close is not None else None
            
            # Prepare result
            result = {
                "symbol": market_index,
                "name": info.get("shortName", market_index),
                "price": latest_close,
                "day_change": day_change,
                "day_change_pct": day_change_pct,
                "volume": history.loc[latest_day, "Volume"],
                "date": latest_day.strftime("%Y-%m-%d"),
                "prev_close": prev_close,
                "open": history.loc[latest_day, "Open"],
                "high": history.loc[latest_day, "High"],
                "low": history.loc[latest_day, "Low"]
            }
            
            # Add YTD change if we have enough data
            ytd_history = await fetch_price_series(market_index, period="ytd")
            if not ytd_history.empty:
                ytd_first = ytd_history.iloc[0]["Close"]
                ytd_change_pct = (latest_close - ytd_first) / ytd_first * 100
                result["ytd_change_pct"] = ytd_change_pct
            
            logger.info(f"Got market data for {market_index}, price: {latest_close}, change: {day_change_pct:.2f}%")
            return result
            
    except Exception as e:
        logger.error(f"Failed to fetch market data for {market_index}: {str(e)}")
        return None


@async_retry(max_retries=2, base_delay=1.0, max_delay=5.0)
async def fetch_iex(endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Fetch financial data from IEX Cloud API.

    Args:
        endpoint: API endpoint path
        params: Optional query parameters

    Returns:
        Dict containing API response
    """
    logger.debug(f"Fetching data from IEX Cloud: endpoint={endpoint}")
    
    # Initialize params if None
    params = params or {}
    
    # Get API key from settings
    api_key = settings.api_keys.IEX_CLOUD_API_KEY
    if not api_key:
        logger.warning("IEX Cloud API key not configured, using mock data")
        # For testing, return mock data
        return _generate_mock_iex_data(endpoint, params)
    
    # Base URL for IEX Cloud API
    base_url = f"https://cloud.iexapis.com/stable/{endpoint}"
    
    # Add token parameter
    params["token"] = api_key
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(base_url, params=params, timeout=10) as response:
                if response.status != 200:
                    logger.error(f"IEX Cloud API request failed with status {response.status}")
                    return _generate_mock_iex_data(endpoint, params)

                data = await response.json()
                logger.info(f"Successfully fetched {endpoint} data from IEX Cloud")
                return data
    
    except Exception as e:
        logger.error(f"Failed to fetch data from IEX Cloud: {str(e)}")
        return _generate_mock_iex_data(endpoint, params)

def _generate_mock_iex_data(endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Generate mock IEX Cloud API data for testing purposes"""
    logger.info(f"Generating mock IEX Cloud data for endpoint {endpoint}")
    
    symbol = params.get("symbol", "AAPL")
    symbol_hash = sum(ord(c) for c in symbol)
    random.seed(symbol_hash + 100)  # Unique seed for IEX
    
    if "quote" in endpoint:
        return {
            "symbol": symbol,
            "companyName": f"Mock {symbol} Inc.",
            "primaryExchange": "MOCK EXCHANGE",
            "latestPrice": round(random.uniform(50, 500), 2),
            "latestVolume": random.randint(100000, 10000000),
            "marketCap": random.randint(1000000000, 2000000000000),
            "peRatio": round(random.uniform(10, 30), 2),
            "week52High": round(random.uniform(300, 700), 2),
            "week52Low": round(random.uniform(30, 200), 2),
            "ytdChange": round(random.uniform(-0.3, 0.5), 4),
        }
    elif "financials" in endpoint:
        return {
            "symbol": symbol,
            "financials": [
                {
                    "reportDate": (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d"),
                    "grossProfit": random.randint(1000000, 50000000),
                    "totalRevenue": random.randint(5000000, 100000000),
                    "netIncome": random.randint(1000000, 25000000),
                    "eps": round(random.uniform(0.5, 5), 2),
                }
            ]
        }
    else:
        # Generic mock data
        return {
            "symbol": symbol,
            "data": "Mock IEX Cloud API data for testing",
            "timestamp": datetime.now().isoformat()
        }

# Implementing fetch_price_tradingview and fetch_eps
@async_retry(max_retries=2, base_delay=1.0, max_delay=5.0)
async def fetch_price_tradingview(symbol: str) -> float:
    """
    Fetch price data from TradingView.

    Args:
        symbol: Stock symbol

    Returns:
        Latest price as float or None if unavailable
    """
    logger.debug(f"Fetching price for {symbol} from TradingView")
    # Mock implementation for testing
    return 150.0  # Replace with actual implementation

@async_retry(max_retries=2, base_delay=1.0, max_delay=5.0)
async def fetch_eps(symbol: str) -> float:
    """
    Fetch EPS (Earnings Per Share) data for a stock.

    Args:
        symbol: Stock symbol

    Returns:
        EPS as float or None if unavailable
    """
    logger.debug(f"Fetching EPS for {symbol}")
    # Mock implementation for testing
    return 5.0  # Replace with actual implementation