import time
from typing import Dict, Any, List, Optional
import aiohttp
import asyncio
from bs4 import BeautifulSoup
from loguru import logger

from backend.monitoring.performance import (
    record_provider_latency,
    record_provider_failure,
    record_provider_success,
    increment_scraping_failure,
    record_cache_hit,
    record_cache_miss,
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
        self._provider_order = [
            "alpha_vantage",
            "polygon",
            "yahoo_finance",
            "finnhub",
            "web_scraper",
        ]

    async def execute_with_monitoring(
        self, provider: str, endpoint: str, operation: callable, *args, **kwargs
    ) -> Dict[str, Any]:
        """Execute operation with full monitoring"""
        start_time = time.time()
        circuit_breaker = self._circuit_breakers[provider]

        if not circuit_breaker.is_closed():
            record_provider_failure(provider, endpoint, "circuit_open")
            raise Exception(f"{provider} circuit breaker is open")

        try:
            result = await operation(*args, **kwargs)
            duration = time.time() - start_time
            record_provider_latency(provider, endpoint, duration)
            record_provider_success(provider)
            circuit_breaker.record_success()
            return result

        except Exception as e:
            error_type = "timeout" if isinstance(e, asyncio.TimeoutError) else "error"
            record_provider_failure(provider, endpoint, error_type)
            circuit_breaker.record_failure()
            raise

    async def fetch_with_fallback(
        self, symbol: str, operation_name: str, operations: Dict[str, callable]
    ) -> Dict[str, Any]:
        """Execute operations with fallback chain"""
        errors = []

        for provider in self._provider_order:
            if provider not in operations:
                continue

            try:
                operation = operations[provider]
                return await self.execute_with_monitoring(
                    provider=provider,
                    endpoint=operation_name,
                    operation=operation,
                    symbol=symbol,
                )
            except Exception as e:
                errors.append(f"{provider}: {str(e)}")
                continue

        error_msg = f"All providers failed for {operation_name}: {', '.join(errors)}"
        logger.error(error_msg)
        raise Exception(error_msg)

    async def fetch_price_data(self, symbol: str) -> Dict[str, Any]:
        """Fetch current price data with fallbacks"""
        operations = {
            "alpha_vantage": self._fetch_price_alpha_vantage,
            "polygon": self._fetch_price_polygon,
            "yahoo_finance": self._fetch_price_yahoo,
            "finnhub": self._fetch_price_finnhub,
            "web_scraper": self._scrape_price,
        }
        return await self.fetch_with_fallback(symbol, "price_data", operations)

    async def _fetch_price_alpha_vantage(self, symbol: str) -> Dict[str, Any]:
        """Fetch price from Alpha Vantage"""
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol,
            "apikey": self.settings.api_keys.ALPHA_VANTAGE_KEY,
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://www.alphavantage.co/query", params=params, timeout=10
            ) as response:
                if response.status != 200:
                    raise Exception(f"Alpha Vantage API error: {response.status}")

                data = await response.json()

                if "Global Quote" not in data:
                    raise Exception("Invalid Alpha Vantage response format")

                quote = data["Global Quote"]
                price = float(quote.get("05. price", 0))

                if price <= 0:
                    raise Exception("Invalid price value")

                return {
                    "price": price,
                    "source": "alpha_vantage",
                    "timestamp": quote.get("07. latest trading day"),
                }

    async def _fetch_price_polygon(self, symbol: str) -> Dict[str, Any]:
        """Fetch price from Polygon"""
        url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/prev"
        params = {"apiKey": self.settings.api_keys.POLYGON_API_KEY}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=10) as response:
                if response.status != 200:
                    raise Exception(f"Polygon API error: {response.status}")

                data = await response.json()

                if not data.get("results"):
                    raise Exception("No results in Polygon response")

                result = data["results"][0]
                price = float(result.get("c", 0))

                if price <= 0:
                    raise Exception("Invalid price value")

                return {
                    "price": price,
                    "source": "polygon",
                    "timestamp": result.get("t"),
                }

    async def _fetch_price_yahoo(self, symbol: str) -> Dict[str, Any]:
        """Fetch price from Yahoo Finance"""
        import yfinance as yf

        # Run yfinance in thread pool since it's synchronous
        loop = asyncio.get_event_loop()

        def get_price():
            ticker = yf.Ticker(symbol)
            info = ticker.info
            price = info.get("regularMarketPrice", 0)
            timestamp = info.get("regularMarketTime", 0)
            return price, timestamp

        price, timestamp = await loop.run_in_executor(None, get_price)

        if price <= 0:
            raise Exception("Invalid price value")

        return {
            "price": float(price),
            "source": "yahoo_finance",
            "timestamp": timestamp,
        }

    async def _fetch_price_finnhub(self, symbol: str) -> Dict[str, Any]:
        """Fetch price from Finnhub"""
        url = "https://finnhub.io/api/v1/quote"
        params = {"symbol": symbol, "token": self.settings.api_keys.FINNHUB_API_KEY}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=10) as response:
                if response.status != 200:
                    raise Exception(f"Finnhub API error: {response.status}")

                data = await response.json()
                price = float(data.get("c", 0))

                if price <= 0:
                    raise Exception("Invalid price value")

                return {"price": price, "source": "finnhub", "timestamp": data.get("t")}

    async def _scrape_price(self, symbol: str) -> Dict[str, Any]:
        """Scrape price from financial websites"""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        sites = [
            ("yahoo", f"https://finance.yahoo.com/quote/{symbol}"),
            ("marketwatch", f"https://www.marketwatch.com/investing/stock/{symbol}"),
            ("investing", f"https://www.investing.com/search/?q={symbol}"),
        ]

        for site_name, url in sites:
            try:
                async with aiohttp.ClientSession(headers=headers) as session:
                    async with session.get(url, timeout=10) as response:
                        if response.status != 200:
                            continue

                        html = await response.text()
                        soup = BeautifulSoup(html, "html.parser")
                        price = self._extract_price(site_name, soup)

                        if price:
                            return {"price": price, "source": f"scrape_{site_name}"}

            except Exception as e:
                increment_scraping_failure(site_name, str(e))
                continue

        raise Exception("Failed to scrape price from any source")

    def _extract_price(self, site: str, soup: BeautifulSoup) -> Optional[float]:
        """Extract price from HTML based on site"""
        try:
            if site == "yahoo":
                elem = soup.select_one('[data-test="qsp-price"]')
            elif site == "marketwatch":
                elem = soup.select_one(".intraday__price .value")
            elif site == "investing":
                elem = soup.select_one(".text-2xl")

            if elem:
                return float(elem.text.strip().replace(",", ""))

        except Exception as e:
            increment_scraping_failure(site, f"parse_error: {str(e)}")

        return None


# Global instance
_unified_provider = None


def get_unified_provider() -> UnifiedDataProvider:
    """Get or create the global UnifiedDataProvider instance"""
    global _unified_provider
    if not _unified_provider:
        _unified_provider = UnifiedDataProvider()
    return _unified_provider
