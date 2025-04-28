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
    'alpha_vantage': CircuitBreaker(name='alpha_vantage', failure_threshold=3, recovery_timeout=300),
    'polygon': CircuitBreaker(name='polygon', failure_threshold=3, recovery_timeout=300),
    'finnhub': CircuitBreaker(name='finnhub', failure_threshold=3, recovery_timeout=300),
    'yahoo_finance': CircuitBreaker(name='yahoo_finance', failure_threshold=3, recovery_timeout=300),
    'web_scraper': CircuitBreaker(name='web_scraper', failure_threshold=5, recovery_timeout=600),
}

# ======== API CLIENTS ========

async def fetch_from_alpha_vantage(endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fetch data from Alpha Vantage API.
    
    Args:
        endpoint: API endpoint path
        params: Query parameters
        
    Returns:
        Dict containing API response
    """
    circuit_breaker = API_CIRCUIT_BREAKERS['alpha_vantage']
    
    if not circuit_breaker.is_closed():
        logger.warning("Alpha Vantage API circuit breaker is open. Using fallback data source.")
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
                    raise Exception(f"Alpha Vantage API request failed with status {response.status}")
                    
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
    circuit_breaker = API_CIRCUIT_BREAKERS['polygon']
    
    if not circuit_breaker.is_closed():
        logger.warning("Polygon API circuit breaker is open. Using fallback data source.")
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
                    raise Exception(f"Polygon API request failed with status {response.status}")
                    
                data = await response.json()
                
                # Check for API error messages
                if data.get("status") == "ERROR":
                    circuit_breaker.record_failure()
                    raise Exception(f"Polygon API error: {data.get('error', 'Unknown error')}")
                    
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
    circuit_breaker = API_CIRCUIT_BREAKERS['finnhub']
    
    if not circuit_breaker.is_closed():
        logger.warning("Finnhub API circuit breaker is open. Using fallback data source.")
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
                    raise Exception(f"Finnhub API request failed with status {response.status}")
                    
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
    circuit_breaker = API_CIRCUIT_BREAKERS['yahoo_finance']
    
    if not circuit_breaker.is_closed():
        logger.warning("Yahoo Finance API circuit breaker is open. Using fallback data source.")
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
            'dates': history.index.strftime('%Y-%m-%d').tolist(),
            'close': history['Close'].tolist(),
            'open': history['Open'].tolist(),
            'high': history['High'].tolist(),
            'low': history['Low'].tolist(),
            'volume': history['Volume'].tolist()
        }
        
        result = {
            'info': info,
            'history': history_dict
        }
        
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
    circuit_breaker = API_CIRCUIT_BREAKERS['web_scraper']
    
    if not circuit_breaker.is_closed():
        logger.warning("Web scraper circuit breaker is open. No fallback available.")
        raise Exception("Web scraper circuit breaker is open")
    
    # List of websites to try scraping from
    scrape_urls = [
        f"https://finance.yahoo.com/quote/{symbol}",
        f"https://www.marketwatch.com/investing/stock/{symbol}",
        f"https://www.investing.com/search/?q={symbol}"
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
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Extract data based on URL
                        if "yahoo.com" in url:
                            # Extract price
                            price_elem = soup.select_one('[data-test="qsp-price"]')
                            if price_elem:
                                result['price'] = float(price_elem.text.replace(',', ''))
                            
                            # Extract EPS
                            eps_elem = soup.select_one('td[data-test="EPS_RATIO-value"]')
                            if eps_elem:
                                eps_text = eps_elem.text.strip()
                                if eps_text and eps_text != "N/A":
                                    result['eps'] = float(eps_text.replace(',', ''))
                            
                            # Extract P/E ratio
                            pe_elem = soup.select_one('td[data-test="PE_RATIO-value"]')
                            if pe_elem:
                                pe_text = pe_elem.text.strip()
                                if pe_text and pe_text != "N/A":
                                    result['pe_ratio'] = float(pe_text.replace(',', ''))
                            
                            # Extract dividend yield
                            div_elem = soup.select_one('[data-test="DIVIDEND_AND_YIELD-value"]')
                            if div_elem:
                                div_text = div_elem.text.strip()
                                if div_text and "N/A" not in div_text and "%" in div_text:
                                    yield_text = div_text.split('(')[1].split(')')[0]
                                    result['dividend_yield'] = float(yield_text.replace('%', '')) / 100
                        
                        elif "marketwatch.com" in url:
                            # Extract price
                            price_elem = soup.select_one('.intraday__price .value')
                            if price_elem:
                                price_text = price_elem.text.strip()
                                result['price'] = float(price_text.replace(',', ''))
                            
                            # Find EPS in table
                            tables = soup.select('.table__cell')
                            for table in tables:
                                if "EPS" in table.text:
                                    next_elem = table.find_next('td')
                                    if next_elem:
                                        eps_text = next_elem.text.strip()
                                        if eps_text and eps_text != "N/A":
                                            try:
                                                result['eps'] = float(eps_text.replace(',', ''))
                                            except:
                                                pass
                        
                        # If we have enough data, break the loop
                        if len(result) >= 3:
                            break
                            
                except Exception as e:
                    logger.warning(f"Error scraping from {url}: {str(e)}")
                    continue
        
        # If we have at least price data, consider it a success
        if 'price' in result:
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
        info = yahoo_data.get('info', {})
        
        # Yahoo Finance provides enterprise value directly
        if 'enterpriseValue' in info and info['enterpriseValue']:
            ev = float(info['enterpriseValue'])
            logger.info(f"Got Enterprise Value {ev} for {symbol} from Yahoo Finance")
            return ev
            
        # Calculate from components if direct EV not available
        elif all(key in info for key in ['marketCap', 'totalDebt', 'totalCash']):
            market_cap = float(info['marketCap'] or 0)
            total_debt = float(info['totalDebt'] or 0)
            cash = float(info['totalCash'] or 0)
            
            ev = market_cap + total_debt - cash
            logger.info(f"Calculated Enterprise Value {ev} for {symbol} from Yahoo Finance components")
            return ev
    except Exception as e:
        logger.warning(f"Failed to get Enterprise Value from Yahoo Finance: {str(e)}")
    
    # Try Alpha Vantage as fallback for company overview
    try:
        av_data = await fetch_from_alpha_vantage("OVERVIEW", {"symbol": symbol})
        
        # Alpha Vantage doesn't directly provide EV, so calculate from components
        if all(key in av_data for key in ['MarketCapitalization', 'TotalDebt', 'Cash']):
            market_cap = float(av_data['MarketCapitalization'])
            total_debt = float(av_data['TotalDebt'])
            cash = float(av_data['Cash'])
            
            ev = market_cap + total_debt - cash
            logger.info(f"Calculated Enterprise Value {ev} for {symbol} from Alpha Vantage components")
            return ev
    except Exception as e:
        logger.warning(f"Failed to get Enterprise Value from Alpha Vantage: {str(e)}")
    
    # Try Finnhub as another fallback
    try:
        finnhub_data = await fetch_from_finnhub("stock/metric", {"symbol": symbol, "metric": "all"})
        metrics = finnhub_data.get('metric', {})
        
        if 'enterpriseValue' in metrics and metrics['enterpriseValue']:
            ev = float(metrics['enterpriseValue'])
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
        info = yahoo_data.get('info', {})
        
        # Yahoo Finance provides EBITDA directly
        if 'ebitda' in info and info['ebitda']:
            ebitda = float(info['ebitda'])
            logger.info(f"Got EBITDA {ebitda} for {symbol} from Yahoo Finance")
            return ebitda
    except Exception as e:
        logger.warning(f"Failed to get EBITDA from Yahoo Finance: {str(e)}")
    
    # Try Alpha Vantage as fallback
    try:
        av_data = await fetch_from_alpha_vantage("OVERVIEW", {"symbol": symbol})
        
        # Alpha Vantage provides EBITDA
        if 'EBITDA' in av_data and av_data['EBITDA']:
            # Handle format differences (e.g., "1.23B" vs numeric)
            ebitda_str = av_data['EBITDA']
            
            # Convert string with possible suffix to float
            if isinstance(ebitda_str, str):
                if ebitda_str.endswith('T'):
                    ebitda = float(ebitda_str[:-1]) * 1e12
                elif ebitda_str.endswith('B'):
                    ebitda = float(ebitda_str[:-1]) * 1e9
                elif ebitda_str.endswith('M'):
                    ebitda = float(ebitda_str[:-1]) * 1e6
                elif ebitda_str.endswith('K'):
                    ebitda = float(ebitda_str[:-1]) * 1e3
                else:
                    ebitda = float(ebitda_str.replace(',', ''))
            else:
                ebitda = float(ebitda_str)
                
            logger.info(f"Got EBITDA {ebitda} for {symbol} from Alpha Vantage")
            return ebitda
    except Exception as e:
        logger.warning(f"Failed to get EBITDA from Alpha Vantage: {str(e)}")
    
    # Try Finnhub as another fallback
    try:
        finnhub_data = await fetch_from_finnhub("stock/metric", {"symbol": symbol, "metric": "all"})
        metrics = finnhub_data.get('metric', {})
        
        if 'ebitdaTTM' in metrics and metrics['ebitdaTTM']:
            ebitda = float(metrics['ebitdaTTM'])
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
    logger.warning(f"Fetching historical Enterprise Value (EV) is not currently supported by the available data providers. Returning None for {symbol}.")
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
        income_data = await fetch_from_alpha_vantage("INCOME_STATEMENT", {"symbol": symbol})
        
        if not income_data or 'quarterlyReports' not in income_data:
            logger.warning(f"No quarterly reports found for {symbol}")
            return None
            
        quarterly_reports = income_data['quarterlyReports']
        
        # Extract EBITDA or calculate it from components
        dates = []
        ebitda_values = []
        
        for report in quarterly_reports:
            # Extract date and convert to datetime
            report_date_str = report.get('fiscalDateEnding')
            if not report_date_str:
                continue
                
            report_date = datetime.strptime(report_date_str, '%Y-%m-%d')
            
            # Skip if before our start date
            if report_date < start_date:
                continue
                
            # Try to get EBITDA directly or calculate from components
            ebitda = None
            
            # Some providers include EBITDA directly
            if 'ebitda' in report and report['ebitda'] and report['ebitda'] != 'None':
                try:
                    ebitda = float(report['ebitda'])
                except (ValueError, TypeError):
                    ebitda = None
                    
            # If not available, calculate from components:
            # EBITDA = Operating Income + Depreciation + Amortization
            if not ebitda and all(k in report for k in ['operatingIncome', 'depreciation']):
                try:
                    operating_income = float(report.get('operatingIncome') or 0)
                    depreciation = float(report.get('depreciation') or 0)
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
        ebitda_series = ebitda_series.resample('Q').last().ffill()
        
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
        history_data = await fetch_historical_prices(symbol, period)
        
        if not history_data or 'dates' not in history_data or not history_data['dates']:
            logger.warning(f"No historical price data found for {symbol}")
            return None
            
        # Convert to pandas Series
        dates = [datetime.strptime(date, '%Y-%m-%d') for date in history_data['dates']]
        close_prices = history_data['close']
        
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
async def fetch_book_value(symbol: str) -> float:
    """
    Fetch the latest book value per share for a company.
    
    Args:
        symbol: Stock symbol
        
    Returns:
        Book Value per Share as float or None if unavailable
    """
    logger.debug(f"Fetching Book Value for {symbol}")
    
    # Try multiple data sources in order
    try:
        # Try Yahoo Finance first
        yahoo_data = await fetch_from_yahoo_finance(symbol)
        info = yahoo_data.get('info', {})
        
        # Yahoo Finance has book value per share
        if 'bookValue' in info and info['bookValue']:
            book_value = float(info['bookValue'])
            logger.info(f"Got Book Value per Share {book_value} for {symbol} from Yahoo Finance")
            return book_value
    except Exception as e:
        logger.warning(f"Failed to get Book Value from Yahoo Finance: {str(e)}")
    
    # Try Alpha Vantage as fallback
    try:
        av_data = await fetch_from_alpha_vantage("OVERVIEW", {"symbol": symbol})
        
        # Alpha Vantage provides book value
        if 'BookValue' in av_data and av_data['BookValue']:
            try:
                book_value = float(av_data['BookValue'])
                logger.info(f"Got Book Value per Share {book_value} for {symbol} from Alpha Vantage")
                return book_value
            except (ValueError, TypeError):
                pass
    except Exception as e:
        logger.warning(f"Failed to get Book Value from Alpha Vantage: {str(e)}")
    
    # If all sources fail, log warning and return None
    logger.error(f"Failed to get Book Value for {symbol} from all sources")
    return None

