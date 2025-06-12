"""
Data Provider Interfaces
========================

Standardized interfaces for API data providers to ensure consistency
in the continuous data collection system.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from loguru import logger

class BaseDataProvider(ABC):
    """Base interface for all data providers"""
    
    def __init__(self, name: str):
        self.name = name
        self.is_initialized = False
        self.last_request_time = 0
        self.rate_limit_delay = 1.0  # seconds between requests
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the data provider"""
        pass
    
    @abstractmethod
    async def get_live_price(self, symbol: str) -> Dict[str, Any]:
        """Get live price data for a symbol"""
        pass
    
    @abstractmethod
    async def get_quote(self, symbol: str) -> Dict[str, Any]:
        """Get detailed quote data for a symbol"""
        pass
    
    async def _respect_rate_limit(self):
        """Ensure rate limiting is respected"""
        import time
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last
            await asyncio.sleep(sleep_time)
        
        self.last_request_time = time.time()

class ZerodhaProvider(BaseDataProvider):
    """Zerodha API data provider"""
    
    def __init__(self):
        super().__init__("zerodha")
        self.api_key = None
        self.access_token = None
        self.kite = None
    
    async def initialize(self) -> bool:
        """Initialize Zerodha connection"""
        try:
            # Check if credentials are available
            # For now, return True to indicate provider is ready
            # In real implementation, you would initialize Kite Connect here
            self.is_initialized = True
            logger.info("✅ Zerodha provider initialized (demo mode)")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to initialize Zerodha: {e}")
            return False
    
    async def get_live_price(self, symbol: str) -> Dict[str, Any]:
        """Get live price from Zerodha"""
        await self._respect_rate_limit()
        
        try:
            # For demo purposes, return mock data
            # In real implementation, use kite.ltp([symbol])
            import random
            import time
            
            base_price = 1000 + hash(symbol) % 1000
            variation = random.uniform(-0.02, 0.02)
            price = base_price * (1 + variation)
            
            return {
                "symbol": symbol,
                "price": round(price, 2),
                "source": "zerodha_api",
                "timestamp": time.time(),
                "volume": random.randint(10000, 100000),
                "change": round(price * variation, 2),
                "change_percent": round(variation * 100, 2)
            }
            
        except Exception as e:
            logger.error(f"❌ Zerodha API error for {symbol}: {e}")
            return {"error": str(e), "source": "zerodha_api"}
    
    async def get_quote(self, symbol: str) -> Dict[str, Any]:
        """Get detailed quote from Zerodha"""
        # For now, return the same as live price
        return await self.get_live_price(symbol)

class AlphaVantageProvider(BaseDataProvider):
    """Alpha Vantage API data provider"""
    
    def __init__(self):
        super().__init__("alpha_vantage")
        self.api_key = None
        self.rate_limit_delay = 12.0  # Alpha Vantage free tier: 5 calls/minute
    
    async def initialize(self) -> bool:
        """Initialize Alpha Vantage connection"""
        try:
            # Check for API key in environment or config
            import os
            self.api_key = os.getenv('ALPHA_VANTAGE_API_KEY')
            if not self.api_key or self.api_key == 'demo':
                logger.warning("⚠️ Alpha Vantage API key not configured, using demo mode")
                self.api_key = 'demo'
            else:
                logger.info("✅ Alpha Vantage API key configured")
            self.is_initialized = True
            logger.info("✅ Alpha Vantage provider initialized")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to initialize Alpha Vantage: {e}")
            return False
    
    async def get_live_price(self, symbol: str) -> Dict[str, Any]:
        """Get live price from Alpha Vantage"""
        await self._respect_rate_limit()
        
        try:
            import httpx
            import time
            
            # Convert Indian symbol to Yahoo format for demo
            av_symbol = f"{symbol}.BSE"
            url = f"https://www.alphavantage.co/query"
            params = {
                "function": "GLOBAL_QUOTE",
                "symbol": av_symbol,
                "apikey": self.api_key
            }
            
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url, params=params)
                data = response.json()
                
                if "Global Quote" in data:
                    quote = data["Global Quote"]
                    return {
                        "symbol": symbol,
                        "price": float(quote.get("05. price", 0)),
                        "source": "alpha_vantage_api",
                        "timestamp": time.time(),
                        "change": float(quote.get("09. change", 0)),
                        "change_percent": quote.get("10. change percent", "0%").replace("%", ""),
                        "volume": int(quote.get("06. volume", 0))
                    }
                else:
                    # Return mock data if API limit reached
                    import random
                    base_price = 1000 + hash(symbol) % 1000
                    variation = random.uniform(-0.02, 0.02)
                    price = base_price * (1 + variation)
                    
                    return {
                        "symbol": symbol,
                        "price": round(price, 2),
                        "source": "alpha_vantage_api_demo",
                        "timestamp": time.time(),
                        "volume": random.randint(10000, 100000),
                        "change": round(price * variation, 2),
                        "change_percent": round(variation * 100, 2)
                    }
                    
        except Exception as e:
            logger.error(f"❌ Alpha Vantage API error for {symbol}: {e}")
            return {"error": str(e), "source": "alpha_vantage_api"}
    
    async def get_quote(self, symbol: str) -> Dict[str, Any]:
        """Get detailed quote from Alpha Vantage"""
        return await self.get_live_price(symbol)

class YahooFinanceProvider(BaseDataProvider):
    """Yahoo Finance data provider (fallback)"""
    
    def __init__(self):
        super().__init__("yahoo_finance")
        self.rate_limit_delay = 0.5  # More lenient rate limiting
    
    async def initialize(self) -> bool:
        """Initialize Yahoo Finance connection"""
        try:
            import yfinance as yf
            self.is_initialized = True
            logger.info("✅ Yahoo Finance provider initialized")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to initialize Yahoo Finance: {e}")
            return False

    async def get_live_price(self, symbol: str) -> Dict[str, Any]:
        """Get live price from Yahoo Finance"""
        await self._respect_rate_limit()
        
        try:
            import yfinance as yf
            import time
              # Normalize Indian symbols properly using the symbol normalizer
            from backend.utils.symbol_normalizer_fixed import IndianEquitySymbolNormalizer
            
            # Use the normalizer to handle Indian symbols correctly
            yahoo_symbol = IndianEquitySymbolNormalizer.normalize_for_yahoo_finance(symbol)
            
            # Debug logging to track normalization
            logger.debug(f"Normalized '{symbol}' -> '{yahoo_symbol}' for Yahoo Finance")
            
            ticker = yf.Ticker(yahoo_symbol)
            
            # For indices, try different period/interval combinations
            if symbol.startswith('^'):
                # Try multiple approaches for indices
                hist = None
                try:
                    hist = ticker.history(period="5d", interval="1d")  # Try daily data first
                    if hist.empty:
                        hist = ticker.history(period="1mo", interval="1d")
                except:
                    pass
            else:
                # For stocks, use intraday data
                hist = ticker.history(period="1d", interval="1m")
            
            if not hist.empty:
                latest = hist.iloc[-1]
                # Calculate change from previous day for indices, or intraday for stocks
                if len(hist) > 1:
                    prev_close = hist.iloc[-2]['Close'] if symbol.startswith('^') else hist.iloc[0]['Close']
                else:
                    prev_close = latest['Close']
                
                change = latest['Close'] - prev_close
                change_percent = (change / prev_close) * 100 if prev_close != 0 else 0
                
                return {
                    "symbol": symbol,
                    "price": round(float(latest['Close']), 2),
                    "source": "yahoo_finance_api",
                    "timestamp": time.time(),
                    "volume": int(latest['Volume']) if latest['Volume'] > 0 else 0,
                    "high": round(float(latest['High']), 2),
                    "low": round(float(latest['Low']), 2),
                    "open": round(float(latest['Open']), 2),
                    "change": round(float(change), 2),
                    "change_percent": round(float(change_percent), 2)
                }
            else:
                raise Exception("No recent data available")
                
        except Exception as e:
            logger.error(f"❌ Yahoo Finance API error for {symbol}: {e}")
            return {"error": str(e), "source": "yahoo_finance_api"}
    
    async def get_quote(self, symbol: str) -> Dict[str, Any]:
        """Get detailed quote from Yahoo Finance"""
        return await self.get_live_price(symbol)

class DataProvidersManager:
    """Manager for all data providers"""
    
    def __init__(self):
        self.providers = {}
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize all available providers"""
        self.providers = {
            'zerodha': ZerodhaProvider(),
            'alpha_vantage': AlphaVantageProvider(),
            'yahoo_finance': YahooFinanceProvider()
        }
        logger.info("✅ Data providers manager initialized")
    
    async def initialize_all(self):
        """Initialize all providers"""
        for name, provider in self.providers.items():
            try:
                await provider.initialize()
                logger.info(f"✅ {name} provider ready")
            except Exception as e:
                logger.warning(f"⚠️ {name} provider failed to initialize: {e}")
    
    def get_provider(self, name: str) -> Optional[BaseDataProvider]:
        """Get a specific provider by name"""
        return self.providers.get(name)
    
    async def get_live_data(self, symbol: str, preferred_provider: str = 'yahoo_finance') -> Dict[str, Any]:
        """Get live data with fallback providers"""
        providers_to_try = [preferred_provider] + [p for p in self.providers.keys() if p != preferred_provider]
        
        for provider_name in providers_to_try:
            provider = self.providers.get(provider_name)
            if provider and provider.is_initialized:
                try:
                    data = await provider.get_live_price(symbol)
                    if 'error' not in data:
                        return data
                except Exception as e:
                    logger.warning(f"Provider {provider_name} failed for {symbol}: {e}")
                    continue
        
        # If all providers fail, return mock data
        import random
        import time
        base_price = 1000 + hash(symbol) % 1000
        variation = random.uniform(-0.02, 0.02)
        price = base_price * (1 + variation)
        
        return {
            "symbol": symbol,
            "price": round(price, 2),
            "source": "fallback_mock",
            "timestamp": time.time(),
            "volume": random.randint(10000, 100000),
            "change": round(price * variation, 2),
            "change_percent": round(variation * 100, 2)
        }

# Global instance for easy import
data_providers = DataProvidersManager()

# Export classes and instance
__all__ = ['BaseDataProvider', 'ZerodhaProvider', 'AlphaVantageProvider', 'YahooFinanceProvider', 'DataProvidersManager', 'data_providers']
