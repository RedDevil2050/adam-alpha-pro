import logging
import asyncio
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple
import pandas as pd

from backend.utils.circuit_breaker import CircuitBreaker
from backend.utils.retry_utils import async_retry, retry, is_rate_limit_error
from backend.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class BaseDataProvider(ABC):
    """
    Abstract base class for all data providers.

    Implements common functionality and resilience patterns like circuit breakers
    and retries that all data providers should use.
    """

    def __init__(self):
        self.name = self.__class__.__name__
        self.settings = get_settings().data_provider

        # Create circuit breaker for this provider
        self.circuit_breaker = CircuitBreaker(
            name=self.name,
            failure_threshold=self.settings.CIRCUIT_BREAKER_THRESHOLD,
            recovery_timeout=self.settings.CIRCUIT_BREAKER_TIMEOUT,
        )

        logger.info(f"Initialized {self.name} data provider")

    @abstractmethod
    async def fetch_price_data(
        self,
        symbol: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        interval: str = "1d",
    ) -> pd.DataFrame:
        """
        Fetch historical price data for a given symbol

        Args:
            symbol: Ticker symbol to fetch data for
            start_date: Start date for historical data
            end_date: End date for historical data (defaults to today)
            interval: Data interval (e.g., "1d" for daily, "1h" for hourly)

        Returns:
            DataFrame with historical price data
        """
        pass

    @abstractmethod
    async def fetch_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch current quote data for a symbol

        Args:
            symbol: Ticker symbol to fetch quote for

        Returns:
            Dictionary with quote data
        """
        pass

    @abstractmethod
    async def search_symbols(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for symbols matching the query

        Args:
            query: Search string for looking up symbols

        Returns:
            List of matching symbols with metadata
        """
        pass

    @abstractmethod
    async def fetch_company_info(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch company information for a symbol

        Args:
            symbol: Ticker symbol to fetch information for

        Returns:
            Dictionary with company information
        """
        pass

    @classmethod
    def get_provider(cls, provider_name: str) -> "BaseDataProvider":
        """
        Factory method to get an instance of a data provider

        Args:
            provider_name: Name of the provider to instantiate

        Returns:
            Instance of a data provider

        Raises:
            ValueError: If the provider is not found
        """
        from backend.data.providers.yahoo_finance_provider import YahooFinanceProvider
        from backend.data.providers.alpha_vantage_provider import AlphaVantageProvider
        from backend.data.providers.polygon_provider import PolygonProvider
        from backend.data.providers.finnhub_provider import FinnhubProvider

        providers = {
            "yahoo_finance": YahooFinanceProvider,
            "alpha_vantage": AlphaVantageProvider,
            "polygon": PolygonProvider,
            "finnhub": FinnhubProvider,
        }

        if provider_name not in providers:
            raise ValueError(
                f"Provider {provider_name} not found. Available providers: {list(providers.keys())}"
            )

        return providers[provider_name]()

    async def execute_with_fallback(self, method_name: str, *args, **kwargs) -> Any:
        """
        Execute a method with fallback to other providers if it fails

        Args:
            method_name: Name of the method to call
            *args: Arguments to pass to the method
            **kwargs: Keyword arguments to pass to the method

        Returns:
            Result from the successful provider call

        Raises:
            Exception: If all providers fail
        """
        # Try primary provider first (self)
        try:
            method = getattr(self, method_name)
            return await method(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Primary provider {self.name} failed: {str(e)}")

        # Try fallback providers
        errors = []
        for provider_name in self.settings.FALLBACK_PROVIDERS:
            try:
                provider = self.get_provider(provider_name)
                method = getattr(provider, method_name)
                result = await method(*args, **kwargs)
                logger.info(f"Fallback to {provider_name} succeeded for {method_name}")
                return result
            except Exception as e:
                errors.append(f"{provider_name}: {str(e)}")
                logger.warning(f"Fallback provider {provider_name} failed: {str(e)}")
                continue

        # All providers failed
        error_msg = f"All providers failed for {method_name}: {', '.join(errors)}"
        logger.error(error_msg)
        raise Exception(error_msg)

    async def execute_with_resilience(self, func, *args, **kwargs) -> Any:
        """
        Execute a function with circuit breaker and retry patterns

        Args:
            func: Function to execute
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function

        Returns:
            Result from the function call

        Raises:
            Exception: If the function fails or circuit breaker is open
        """
        # Check if circuit is open
        if not self.circuit_breaker.allow_request():
            logger.warning(f"Circuit breaker open for {self.name}, request not allowed")
            raise Exception(f"Circuit breaker open for {self.name}")

        # Define retry decorated function
        @async_retry(
            max_retries=self.settings.MAX_RETRIES,
            backoff_factor=self.settings.RETRY_BACKOFF,
            retry_exceptions=(Exception,),
            on_retry=lambda retry_num, e: logger.warning(
                f"Retrying {func.__name__} (attempt {retry_num}) after error: {str(e)}"
            ),
        )
        async def _execute_with_retry():
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Record failure for circuit breaker
                self.circuit_breaker.record_failure()

                # Re-raise for retry
                raise

        try:
            result = await _execute_with_retry()
            # Record success for circuit breaker
            self.circuit_breaker.record_success()
            return result
        except Exception as e:
            # If we get here, retries have been exhausted
            logger.error(
                f"{self.name} request failed after {self.settings.MAX_RETRIES} retries: {str(e)}"
            )
            raise
