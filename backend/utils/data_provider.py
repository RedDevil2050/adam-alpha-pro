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

# ======== UNIFIED PUBLIC API ========

@async_retry(max_retries=2, base_delay=1.0, max_delay=5.0)
async def fetch_price_point(symbol: str) -> float:
    """
    Fetch the latest price for a symbol from any available source.
    
    Args:
        symbol: Stock symbol
        
    Returns:
        Current price as float
    """
    logger.debug(f"Fetching price point for {symbol}")
    
    # Try multiple data sources in order
    sources_to_try = [
        (fetch_from_alpha_vantage, {"endpoint": "GLOBAL_QUOTE", "params": {"symbol": symbol}}),
        (fetch_from_polygon, {"endpoint": f"aggs/ticker/{symbol}/prev", "params": {}}),
        (fetch_from_yahoo_finance, {"symbol": symbol}),
        (fetch_from_finnhub, {"endpoint": "quote", "params": {"symbol": symbol}}),
        (scrape_stock_data, {"symbol": symbol})
    ]
    
    for source_func, kwargs in sources_to_try:
        try:
            if source_func.__name__ == 'fetch_from_alpha_vantage':
                data = await source_func(**kwargs)
                price = float(data.get('Global Quote', {}).get('05. price', 0))
            elif source_func.__name__ == 'fetch_from_polygon':
                data = await source_func(**kwargs)
                price = float(data.get('results', [{}])[0].get('c', 0))
            elif source_func.__name__ == 'fetch_from_yahoo_finance':
                data = await source_func(**kwargs)
                price = float(data.get('info', {}).get('currentPrice', 0))
            elif source_func.__name__ == 'fetch_from_finnhub':
                data = await source_func(**kwargs)
                price = float(data.get('c', 0))
            else:  # Web scraper
                data = await source_func(**kwargs)
                price = float(data.get('price', 0))
            
            if price > 0:
                logger.info(f"Got price {price} for {symbol} from {source_func.__name__}")
                return price
                
        except Exception as e:
            logger.warning(f"Failed to get price from {source_func.__name__}: {str(e)}")
            continue
    
    # If all sources fail, raise exception
    logger.error(f"Failed to get price for {symbol} from all sources")
    raise Exception(f"Could not fetch price for {symbol} from any data source")

@async_retry(max_retries=2, base_delay=1.0, max_delay=5.0)
async def fetch_eps_data(symbol: str) -> Dict[str, Any]:
    """
    Fetch detailed EPS data for a symbol from any available source.
    
    Args:
        symbol: Stock symbol
        
    Returns:
        Dict with EPS data (eps, price, pe_ratio, dividend_yield)
    """
    logger.debug(f"Fetching EPS data for {symbol}")
    
    # Try multiple data sources in order
    sources = [
        (fetch_from_alpha_vantage, {"endpoint": "OVERVIEW", "params": {"symbol": symbol}}),
        (fetch_from_yahoo_finance, {"symbol": symbol}),
        (scrape_stock_data, {"symbol": symbol})
    ]
    
    result = {}
    
    for source_func, kwargs in sources:
        try:
            if source_func.__name__ == 'fetch_from_alpha_vantage':
                data = await source_func(**kwargs)
                result = {
                    'eps': float(data.get('EPS', 0)),
                    'pe_ratio': float(data.get('PERatio', 0)),
                    'dividend_yield': float(data.get('DividendYield', 0)),
                }
                
                # Fetch price separately
                price = await fetch_price_point(symbol)
                result['price'] = price
                
            elif source_func.__name__ == 'fetch_from_yahoo_finance':
                data = await source_func(**kwargs)
                info = data.get('info', {})
                result = {
                    'eps': float(info.get('trailingEPS', 0) or 0),
                    'price': float(info.get('currentPrice', 0) or 0),
                    'pe_ratio': float(info.get('trailingPE', 0) or 0),
                    'dividend_yield': float(info.get('dividendYield', 0) or 0)
                }
                
            else:  # Web scraper
                result = await source_func(**kwargs)
            
            # Check if we have valid data
            if result.get('price', 0) > 0:
                # Fill in missing values if possible
                if 'eps' in result and 'price' in result and result['eps'] > 0 and 'pe_ratio' not in result:
                    result['pe_ratio'] = result['price'] / result['eps']
                    
                logger.info(f"Got EPS data for {symbol} from {source_func.__name__}")
                return result
                
        except Exception as e:
            logger.warning(f"Failed to get EPS data from {source_func.__name__}: {str(e)}")
            continue
    
    # If all sources fail, raise exception
    logger.error(f"Failed to get EPS data for {symbol} from all sources")
    raise Exception(f"Could not fetch EPS data for {symbol} from any data source")

@async_retry(max_retries=2, base_delay=1.0, max_delay=5.0)
async def fetch_historical_prices(
    symbol: str, 
    period: str = "1mo"
) -> Dict[str, List[float]]:
    """
    Fetch historical price data for a symbol.
    
    Args:
        symbol: Stock symbol
        period: Time period to fetch (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y)
        
    Returns:
        Dict with dates and OHLCV data
    """
    logger.debug(f"Fetching historical prices for {symbol}, period={period}")
    
    # Try Yahoo Finance first (most reliable for historical data)
    try:
        data = await fetch_from_yahoo_finance(symbol)
        history = data.get('history', {})
        
        if history and len(history.get('dates', [])) > 0:
            return history
            
    except Exception as e:
        logger.warning(f"Failed to get historical data from Yahoo Finance: {str(e)}")
    
    # Try Alpha Vantage as fallback
    try:
        # Select appropriate Alpha Vantage function based on period
        if period in ["1d", "5d"]:
            function = "TIME_SERIES_INTRADAY"
            params = {"symbol": symbol, "interval": "60min", "outputsize": "full"}
        else:
            function = "TIME_SERIES_DAILY"
            params = {"symbol": symbol, "outputsize": "full"}
            
        data = await fetch_from_alpha_vantage(function, params)
        
        # Parse Alpha Vantage response
        time_series_key = next((key for key in data.keys() if 'Time Series' in key), None)
        if time_series_key:
            time_series = data[time_series_key]
            
            # Convert to desired format
            dates = []
            close_prices = []
            open_prices = []
            high_prices = []
            low_prices = []
            volumes = []
            
            for date, values in time_series.items():
                dates.append(date)
                close_prices.append(float(values['4. close']))
                open_prices.append(float(values['1. open']))
                high_prices.append(float(values['2. high']))
                low_prices.append(float(values['3. low']))
                volumes.append(float(values['5. volume']))
            
            # Limit to requested period
            if period == "1d":
                limit = 1
            elif period == "5d":
                limit = 5
            elif period == "1mo":
                limit = 21
            elif period == "3mo":
                limit = 63
            elif period == "6mo":
                limit = 126
            elif period == "1y":
                limit = 252
            else:
                limit = len(dates)
                
            history = {
                'dates': dates[:limit],
                'close': close_prices[:limit],
                'open': open_prices[:limit],
                'high': high_prices[:limit],
                'low': low_prices[:limit],
                'volume': volumes[:limit]
            }
            
            return history
    
    except Exception as e:
        logger.warning(f"Failed to get historical data from Alpha Vantage: {str(e)}")
    
    # If all sources fail, raise exception
    logger.error(f"Failed to get historical data for {symbol} from all sources")
    raise Exception(f"Could not fetch historical data for {symbol} from any data source")

@async_retry(max_retries=2, base_delay=1.0, max_delay=5.0)
async def fetch_market_data(symbol: str) -> Dict[str, Any]:
    """
    Fetch comprehensive market data for a symbol from any available source.
    
    Args:
        symbol: Stock symbol
        
    Returns:
        Dict with consolidated market data
    """
    logger.debug(f"Fetching market data for {symbol}")
    
    result = {}
    
    # Try to get detailed stock info from Yahoo Finance
    try:
        yahoo_data = await fetch_from_yahoo_finance(symbol)
        result = yahoo_data.get('info', {})
    except Exception as e:
        logger.warning(f"Failed to get Yahoo Finance data: {str(e)}")
    
    # Try to get EPS data if not already present
    if 'trailingEPS' not in result:
        try:
            eps_data = await fetch_eps_data(symbol)
            result['eps'] = eps_data.get('eps')
            result['pe_ratio'] = eps_data.get('pe_ratio')
            result['dividend_yield'] = eps_data.get('dividend_yield')
        except Exception as e:
            logger.warning(f"Failed to get EPS data: {str(e)}")
    
    # Get current price if not already present
    if 'currentPrice' not in result:
        try:
            result['currentPrice'] = await fetch_price_point(symbol)
        except Exception as e:
            logger.warning(f"Failed to get current price: {str(e)}")
    
    # Check if we have enough data
    required_fields = ['currentPrice', 'eps', 'pe_ratio']
    
    # Handle missing fields with fallbacks
    missing_fields = [field for field in required_fields if field not in result or not result[field]]
    
    if missing_fields:
        logger.warning(f"Missing fields in market data for {symbol}: {missing_fields}")
        
        # Try web scraping as last resort
        try:
            scraped_data = await scrape_stock_data(symbol)
            
            # Update missing fields
            for field in missing_fields:
                if field == 'currentPrice' and 'price' in scraped_data:
                    result['currentPrice'] = scraped_data['price']
                elif field in scraped_data:
                    result[field] = scraped_data[field]
        except Exception as e:
            logger.warning(f"Failed to scrape data for missing fields: {str(e)}")
    
    return result

