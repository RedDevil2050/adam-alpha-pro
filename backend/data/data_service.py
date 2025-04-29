import yfinance as yf
import pandas as pd
import redis
import logging
from typing import List, Dict, Optional, Union, Any
import asyncio
import aiohttp
from datetime import datetime, timedelta
from functools import lru_cache
from .providers.unified_provider import UnifiedDataProvider, get_unified_provider
from backend.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class DataService:
    def __init__(self):
        self.data_provider = get_unified_provider()
        try:
            self.cache = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=0,
                decode_responses=True,
            )
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            self.cache = None
        self.rate_limiter = asyncio.Semaphore(5)

    async def get_market_data(
        self, symbols: List[str], lookback_period: int = 252
    ) -> Dict[str, Any]:
        """Enhanced resilient data collection that always returns data"""
        results = {}
        errors = []

        for symbol in symbols:
            try:
                # Try to get from cache first
                cache_key = f"market_data_{symbol}"
                cached = self._get_from_cache(cache_key)
                if cached:
                    results[symbol] = cached
                    continue

                # Get fresh data with fallbacks
                data = await self.data_provider.fetch_data_resilient(symbol, "price")
                if data["data"]:
                    results[symbol] = {
                        "price": data["data"].get("price", 0),
                        "source": data["source"],
                        "confidence": data["confidence"]
                    }
                    # Cache only high/medium confidence data
                    if data["confidence"] in ["high", "medium"]:
                        self._cache_data(cache_key, results[symbol])
                else:
                    results[symbol] = {
                        "price": 0,
                        "source": "none",
                        "confidence": "none",
                        "error": "No data available"
                    }
            except Exception as e:
                errors.append(f"{symbol}: {str(e)}")
                results[symbol] = {
                    "price": 0,
                    "source": "error",
                    "confidence": "none",
                    "error": str(e)
                }

        return {
            "data": results,
            "errors": errors if errors else None,
            "timestamp": datetime.now().isoformat()
        }

    async def get_detailed_quote(self, symbol: str) -> Dict[str, Any]:
        """Get comprehensive quote data with fallbacks for each field"""
        async def get_field(field_type: str) -> Dict[str, Any]:
            return await self.data_provider.fetch_data_resilient(symbol, field_type)

        # Fetch different data types in parallel
        price_data, volume_data, market_cap_data = await asyncio.gather(
            get_field("price"),
            get_field("volume"),
            get_field("market_cap")
        )

        return {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "price": {
                "value": price_data["data"].get("price", 0),
                "source": price_data["source"],
                "confidence": price_data["confidence"]
            },
            "volume": {
                "value": volume_data["data"].get("volume", 0),
                "source": volume_data["source"],
                "confidence": volume_data["confidence"]
            },
            "market_cap": {
                "value": market_cap_data["data"].get("market_cap", 0),
                "source": market_cap_data["source"],
                "confidence": market_cap_data["confidence"]
            }
        }

    def _get_from_cache(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve data from cache"""
        try:
            if self.cache:
                cached = self.cache.get(key)
                if cached:
                    return eval(cached)  # Safe since we control what goes into cache
        except Exception as e:
            logger.error(f"Cache retrieval error: {e}")
        return None

    def _cache_data(self, key: str, data: Dict[str, Any], expiry: int = 300):
        """Cache market data with expiration"""
        try:
            if self.cache:
                self.cache.setex(key, expiry, str(data))
        except Exception as e:
            logger.error(f"Cache storage error: {e}")
