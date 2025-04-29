import time
from typing import Dict, Any, List, Optional
import aiohttp
import asyncio
from bs4 import BeautifulSoup
from loguru import logger
import httpx
import yfinance as yf
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import re

from backend.monitoring.performance import (
    record_provider_latency,
    record_provider_failure,
    record_provider_success,
    increment_scraping_failure,
    record_cache_hit,
    record_cache_miss,
    record_collection_attempt,
    record_collection_latency,
    record_source_switch,
    record_data_quality,
)
from backend.data.providers.base_provider import BaseDataProvider
from backend.utils.circuit_breaker import CircuitBreaker
from backend.config.settings import get_settings

class UnifiedDataProvider(BaseDataProvider):
    """
    Enhanced data provider with comprehensive monitoring and resilience
    """

    def __init__(self):
        super().__init__()
        self.settings = get_settings()
        self._circuit_breakers = {
            "alpha_vantage": CircuitBreaker(name="alpha_vantage", failure_threshold=3, recovery_timeout=300),
            "polygon": CircuitBreaker(name="polygon", failure_threshold=3, recovery_timeout=300),
            "finnhub": CircuitBreaker(name="finnhub", failure_threshold=3, recovery_timeout=300),
            "yahoo_finance": CircuitBreaker(name="yahoo_finance", failure_threshold=3, recovery_timeout=300),
            "web_scraper": CircuitBreaker(name="web_scraper", failure_threshold=5, recovery_timeout=600),
        }
        self._provider_order = ["alpha_vantage", "polygon", "yahoo_finance", "finnhub", "web_scraper"]
        self._executor = ThreadPoolExecutor(max_workers=3)
        self._scraping_sites = [
            ("yahoo", "https://finance.yahoo.com/quote/{symbol}"),
            ("marketwatch", "https://www.marketwatch.com/investing/stock/{symbol}"),
            ("investing", "https://www.investing.com/equities/{symbol}"),
            ("google", "https://www.google.com/finance/quote/{symbol}"),
        ]

    async def fetch_data_resilient(self, symbol: str, data_type: str) -> Dict[str, Any]:
        """
        Fetch data with automatic fallback to web scraping.
        Always returns some data, even if approximate or from backup source.
        """
        start_time = time.monotonic()
        current_source = None
        record_collection_attempt(symbol, data_type)
        
        results = []
        errors = []

        # Try API providers first
        for provider in self._provider_order[:-1]:  # Exclude web_scraper
            try:
                if not self._circuit_breakers[provider].is_closed():
                    continue

                if current_source:
                    record_source_switch(symbol, current_source, provider)
                current_source = provider

                result = await self._fetch_from_provider(provider, symbol, data_type)
                if result:
                    results.append((provider, result))
                    self._circuit_breakers[provider].record_success()
                    
                    # Return early if we have high confidence data
                    if provider in ["alpha_vantage", "polygon"]:
                        confidence = 1.0  # High confidence
                        record_data_quality(symbol, data_type, provider, confidence)
                        duration = time.monotonic() - start_time
                        record_collection_latency(symbol, data_type, provider, duration)
                        return {"source": provider, "data": result, "confidence": "high"}

            except Exception as e:
                self._circuit_breakers[provider].record_failure()
                errors.append(f"{provider}: {str(e)}")
                continue

        # If no API data, try web scraping immediately and in parallel
        if not results:
            if current_source:
                record_source_switch(symbol, current_source, "web_scraper")
            current_source = "web_scraper"

            scraping_results = await self._parallel_scrape(symbol, data_type)
            if scraping_results:
                results.extend([("web_scraper", r) for r in scraping_results])

        # If we have any results, return the best one
        if results:
            # Prioritize results by source reliability
            for provider, result in results:
                confidence = 1.0 if provider in ["alpha_vantage", "polygon"] else 0.7
                record_data_quality(symbol, data_type, provider, confidence)
                confidence_level = "high" if provider in ["alpha_vantage", "polygon"] else "medium"
                duration = time.monotonic() - start_time
                record_collection_latency(symbol, data_type, provider, duration)
                return {"source": provider, "data": result, "confidence": confidence_level}

        # Last resort: Return approximate/derived data
        if current_source:
            record_source_switch(symbol, current_source, "fallback")
        
        fallback_data = await self._generate_fallback_data(symbol, data_type)
        duration = time.monotonic() - start_time
        record_collection_latency(symbol, data_type, "fallback", duration)
        record_data_quality(symbol, data_type, "fallback", 0.3)  # Low confidence
        return {"source": "fallback", "data": fallback_data, "confidence": "low"}

    async def _fetch_from_provider(self, provider: str, symbol: str, data_type: str) -> Optional[Dict[str, Any]]:
        """Fetch data from a specific provider"""
        start_time = time.monotonic()
        try:
            if provider == "yahoo_finance":
                return await self._fetch_yahoo(symbol, data_type)
            elif provider == "alpha_vantage":
                return await self._fetch_alpha_vantage(symbol, data_type)
            elif provider == "polygon":
                return await self._fetch_polygon(symbol, data_type)
            elif provider == "finnhub":
                return await self._fetch_finnhub(symbol, data_type)
        except Exception as e:
            record_provider_failure(provider, data_type, str(e))
            raise
        finally:
            duration = time.monotonic() - start_time
            record_provider_latency(provider, data_type, duration)

    async def _parallel_scrape(self, symbol: str, data_type: str) -> List[Dict[str, Any]]:
        """Scrape data from multiple sources in parallel"""
        tasks = []
        async with httpx.AsyncClient(timeout=10) as client:
            for site_name, url_template in self._scraping_sites:
                url = url_template.format(symbol=symbol)
                tasks.append(self._scrape_single_site(client, site_name, url, data_type))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return [r for r in results if isinstance(r, dict)]

    async def _scrape_single_site(self, client: httpx.AsyncClient, site: str, url: str, data_type: str) -> Optional[Dict[str, Any]]:
        """Scrape data from a single website"""
        try:
            response = await client.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            return self._extract_data(site, soup, data_type)
        except Exception as e:
            increment_scraping_failure(site, str(e))
            return None

    def _extract_data(self, site: str, soup: BeautifulSoup, data_type: str) -> Optional[Dict[str, Any]]:
        """Extract specific data type from HTML based on site"""
        try:
            if site == "yahoo":
                return self._extract_yahoo(soup, data_type)
            elif site == "marketwatch":
                return self._extract_marketwatch(soup, data_type)
            elif site == "investing":
                return self._extract_investing(soup, data_type)
            elif site == "google":
                return self._extract_google(soup, data_type)
        except Exception as e:
            increment_scraping_failure(site, f"parse_error: {str(e)}")
        return None

    def _extract_yahoo(self, soup: BeautifulSoup, data_type: str) -> Optional[Dict[str, Any]]:
        """Extract data from Yahoo Finance"""
        result = {}
        
        if data_type == "price":
            elem = soup.select_one('[data-test="qsp-price"]')
            if elem:
                result["price"] = float(elem.text.replace(",", ""))
        elif data_type == "volume":
            elem = soup.select_one('[data-test="TD_VOLUME-value"]')
            if elem:
                result["volume"] = float(elem.text.replace(",", ""))
        elif data_type == "market_cap":
            elem = soup.select_one('[data-test="MARKET_CAP-value"]')
            if elem:
                text = elem.text.strip().lower()
                multiplier = 1
                if 't' in text:
                    multiplier = 1e12
                elif 'b' in text:
                    multiplier = 1e9
                elif 'm' in text:
                    multiplier = 1e6
                value = float(re.search(r'[\d.]+', text).group()) * multiplier
                result["market_cap"] = value

        return result if result else None

    def _extract_marketwatch(self, soup: BeautifulSoup, data_type: str) -> Optional[Dict[str, Any]]:
        """Extract data from MarketWatch"""
        result = {}
        
        if data_type == "price":
            elem = soup.select_one(".intraday__price .value")
            if elem:
                result["price"] = float(elem.text.replace(",", ""))
        elif data_type == "volume":
            elem = soup.select_one(".volume__value")
            if elem:
                text = elem.text.strip().lower()
                multiplier = 1
                if 'm' in text:
                    multiplier = 1e6
                elif 'k' in text:
                    multiplier = 1e3
                value = float(re.search(r'[\d.]+', text).group()) * multiplier
                result["volume"] = value

        return result if result else None

    def _extract_investing(self, soup: BeautifulSoup, data_type: str) -> Optional[Dict[str, Any]]:
        """Extract data from Investing.com"""
        result = {}
        
        if data_type == "price":
            elem = soup.select_one(".instrument-price_last__KQzyA")
            if elem:
                result["price"] = float(elem.text.replace(",", ""))
        elif data_type == "volume":
            elem = soup.select_one("dd[data-test='volume']")
            if elem:
                text = elem.text.strip().lower()
                multiplier = 1
                if 'm' in text:
                    multiplier = 1e6
                elif 'k' in text:
                    multiplier = 1e3
                value = float(re.search(r'[\d.]+', text).group()) * multiplier
                result["volume"] = value

        return result if result else None

    def _extract_google(self, soup: BeautifulSoup, data_type: str) -> Optional[Dict[str, Any]]:
        """Extract data from Google Finance"""
        result = {}
        
        if data_type == "price":
            elem = soup.select_one(".YMlKec.fxKbKc")
            if elem:
                result["price"] = float(elem.text.replace(",", ""))
        elif data_type == "market_cap":
            elem = soup.select_one("[data-metric='Market cap'] .P6K39c")
            if elem:
                text = elem.text.strip().lower()
                multiplier = 1
                if 't' in text:
                    multiplier = 1e12
                elif 'b' in text:
                    multiplier = 1e9
                elif 'm' in text:
                    multiplier = 1e6
                value = float(re.search(r'[\d.]+', text).group()) * multiplier
                result["market_cap"] = value

        return result if result else None

    async def _generate_fallback_data(self, symbol: str, data_type: str) -> Dict[str, Any]:
        """Generate approximate data when all other sources fail"""
        try:
            # Run yfinance in thread pool as last resort
            ticker = await asyncio.get_event_loop().run_in_executor(
                self._executor, lambda: yf.Ticker(symbol)
            )
            
            if data_type == "price":
                try:
                    hist = ticker.history(period="1d")
                    if not hist.empty:
                        return {"price": float(hist["Close"].iloc[-1])}
                except:
                    pass
                    
            # Additional fallback calculations based on data_type
            return await self._calculate_fallback_value(symbol, data_type)
            
        except Exception as e:
            logger.error(f"Fallback data generation failed: {e}")
            # Return estimated data with warning
            return {
                "estimated": True,
                "warning": "Data is approximated",
                "value": await self._estimate_value(symbol, data_type)
            }

    async def _calculate_fallback_value(self, symbol: str, data_type: str) -> Dict[str, Any]:
        """Calculate approximate values using available data"""
        # Implementation of fallback calculations
        if data_type == "price":
            # Use technical analysis or historical patterns
            return {"price": await self._estimate_price(symbol)}
        elif data_type == "volume":
            # Use average volume
            return {"volume": await self._estimate_volume(symbol)}
        # Add other data types as needed
        return {"value": None, "warning": "No estimation available"}

    async def _estimate_price(self, symbol: str) -> float:
        """Estimate price using moving averages or other technicals"""
        try:
            # Use thread pool for synchronous operations
            def get_historical():
                return yf.download(symbol, period="5d", progress=False)
            
            hist = await asyncio.get_event_loop().run_in_executor(self._executor, get_historical)
            if not hist.empty:
                return float(hist["Close"].mean())
        except:
            pass
        return 0.0

    async def _estimate_volume(self, symbol: str) -> float:
        """Estimate volume using historical averages"""
        try:
            def get_volume():
                return yf.download(symbol, period="30d", progress=False)["Volume"].mean()
            
            return float(await asyncio.get_event_loop().run_in_executor(self._executor, get_volume))
        except:
            return 0.0

    async def _estimate_value(self, symbol: str, data_type: str) -> float:
        """Final fallback to estimate values when no data is available"""
        if data_type == "price":
            return await self._estimate_price(symbol)
        elif data_type == "volume":
            return await self._estimate_volume(symbol)
        elif data_type == "market_cap":
            # Estimate market cap from price and typical volume
            try:
                price = await self._estimate_price(symbol)
                volume = await self._estimate_volume(symbol)
                return price * volume
            except:
                return 0.0
        return 0.0

    async def _fetch_yahoo(self, symbol: str, data_type: str) -> Optional[Dict[str, Any]]:
        """Fetch data from Yahoo Finance API"""
        try:
            def get_ticker_data():
                ticker = yf.Ticker(symbol)
                if data_type == "price":
                    hist = ticker.history(period="1d")
                    if not hist.empty:
                        return {"price": float(hist["Close"].iloc[-1])}
                elif data_type == "volume":
                    hist = ticker.history(period="1d")
                    if not hist.empty:
                        return {"volume": float(hist["Volume"].iloc[-1])}
                elif data_type == "market_cap":
                    info = ticker.info
                    if "marketCap" in info:
                        return {"market_cap": float(info["marketCap"])}
                return None

            return await asyncio.get_event_loop().run_in_executor(self._executor, get_ticker_data)
        except Exception as e:
            logger.error(f"Yahoo Finance API error: {str(e)}")
            raise

    async def _fetch_alpha_vantage(self, symbol: str, data_type: str) -> Optional[Dict[str, Any]]:
        """Fetch data from Alpha Vantage API"""
        api_key = self.settings.api_keys.ALPHA_VANTAGE_KEY
        if not api_key:
            raise ValueError("Alpha Vantage API key not configured")

        base_url = "https://www.alphavantage.co/query"
        params = {"symbol": symbol, "apikey": api_key}

        if data_type == "price":
            params["function"] = "GLOBAL_QUOTE"
            async with aiohttp.ClientSession() as session:
                async with session.get(base_url, params=params) as response:
                    if response.status != 200:
                        raise Exception(f"Alpha Vantage API error: {response.status}")
                    data = await response.json()
                    if "Global Quote" in data:
                        quote = data["Global Quote"]
                        if "05. price" in quote:
                            return {"price": float(quote["05. price"])}

        elif data_type == "volume":
            params["function"] = "GLOBAL_QUOTE"
            async with aiohttp.ClientSession() as session:
                async with session.get(base_url, params=params) as response:
                    if response.status != 200:
                        raise Exception(f"Alpha Vantage API error: {response.status}")
                    data = await response.json()
                    if "Global Quote" in data:
                        quote = data["Global Quote"]
                        if "06. volume" in quote:
                            return {"volume": float(quote["06. volume"])}

        return None

    async def _fetch_polygon(self, symbol: str, data_type: str) -> Optional[Dict[str, Any]]:
        """Fetch data from Polygon.io API"""
        api_key = self.settings.api_keys.POLYGON_API_KEY
        if not api_key:
            raise ValueError("Polygon API key not configured")

        headers = {"Authorization": f"Bearer {api_key}"}
        
        if data_type == "price":
            url = f"https://api.polygon.io/v2/last/trade/{symbol}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        raise Exception(f"Polygon API error: {response.status}")
                    data = await response.json()
                    if data.get("status") == "OK":
                        return {"price": float(data["results"]["p"])}

        elif data_type == "volume":
            # Get aggregate data for today
            from_date = datetime.now().strftime("%Y-%m-%d")
            url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/{from_date}/{from_date}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        raise Exception(f"Polygon API error: {response.status}")
                    data = await response.json()
                    if data.get("status") == "OK" and data.get("results"):
                        return {"volume": float(data["results"][0]["v"])}

        return None

    async def _fetch_finnhub(self, symbol: str, data_type: str) -> Optional[Dict[str, Any]]:
        """Fetch data from Finnhub API"""
        api_key = self.settings.api_keys.FINNHUB_API_KEY
        if not api_key:
            raise ValueError("Finnhub API key not configured")

        base_url = "https://finnhub.io/api/v1"
        headers = {"X-Finnhub-Token": api_key}

        if data_type == "price":
            url = f"{base_url}/quote"
            params = {"symbol": symbol}
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers) as response:
                    if response.status != 200:
                        raise Exception(f"Finnhub API error: {response.status}")
                    data = await response.json()
                    if "c" in data:  # Current price
                        return {"price": float(data["c"])}

        elif data_type == "volume":
            url = f"{base_url}/quote"
            params = {"symbol": symbol}
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers) as response:
                    if response.status != 200:
                        raise Exception(f"Finnhub API error: {response.status}")
                    data = await response.json()
                    if "v" in data:  # Current volume
                        return {"volume": float(data["v"])}

        return None
