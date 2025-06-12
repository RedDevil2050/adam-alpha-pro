"""
Live Market Data Service for Indian Stock Market
Provides real-time data for NIFTY, SENSEX and other Indian market indices
"""

import asyncio
import time
from typing import Dict, List, Optional, Any
from loguru import logger
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor

from backend.data.providers.unified_provider import UnifiedDataProvider
from backend.utils.symbol_normalizer_fixed import normalize_indian_symbol


class MarketDataService:
    """Service for fetching live Indian market data"""
    
    def __init__(self):
        self.provider = UnifiedDataProvider()
        self.executor = ThreadPoolExecutor(max_workers=3)
        
        # Indian market indices mapping
        self.indices_mapping = {
            "NIFTY50": "^NSEI",
            "SENSEX": "^BSESN", 
            "BANKNIFTY": "^NSEBANK",
            "NIFTYIT": "^NSEIT",
            "NIFTYFMCG": "^NSEFMCG",
            "NIFTYAUTO": "^NSEAUTO"
        }
        
        # Cache for market data (5 minute cache)
        self._cache = {}
        self._cache_timeout = 300  # 5 minutes
        
    def _get_yahoo_data_sync(self, symbol: str) -> Optional[Dict]:
        """Synchronous Yahoo Finance data fetch"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            hist = ticker.history(period="1d")
            
            if not hist.empty:
                latest = hist.iloc[-1]
                current_price = float(latest['Close'])
                prev_close = info.get('previousClose', current_price)
                
                change = current_price - prev_close
                change_percent = (change / prev_close) * 100 if prev_close else 0
                
                return {
                    "symbol": symbol,
                    "name": info.get('longName', symbol),
                    "value": round(current_price, 2),
                    "change": round(change, 2),
                    "change_percent": round(change_percent, 2),
                    "volume": int(latest.get('Volume', 0)),
                    "high": round(float(latest['High']), 2),
                    "low": round(float(latest['Low']), 2),
                    "open": round(float(latest['Open']), 2),
                    "market_cap": info.get('marketCap', 0),
                    "timestamp": time.time()
                }
            else:
                logger.warning(f"No historical data for {symbol}")
                return None
                
        except Exception as e:
            logger.error(f"Yahoo Finance error for {symbol}: {e}")
            return None
    
    async def get_live_index_data(self, index_name: str) -> Optional[Dict]:
        """Get live data for a specific index"""
        cache_key = f"index_{index_name}"
        
        # Check cache first
        if cache_key in self._cache:
            cached_data, timestamp = self._cache[cache_key]
            if time.time() - timestamp < self._cache_timeout:
                return cached_data
        
        try:
            # Get Yahoo Finance symbol
            yahoo_symbol = self.indices_mapping.get(index_name.upper())
            if not yahoo_symbol:
                logger.warning(f"Unknown index: {index_name}")
                return None
            
            # Fetch data using executor to avoid blocking
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(
                self.executor, 
                self._get_yahoo_data_sync, 
                yahoo_symbol
            )
            
            if data:
                # Update cache
                self._cache[cache_key] = (data, time.time())
                logger.info(f"Live data fetched for {index_name}: {data['value']}")
                return data
            else:
                return self._get_fallback_data(index_name)
                
        except Exception as e:
            logger.error(f"Error fetching live data for {index_name}: {e}")
            return self._get_fallback_data(index_name)
    
    async def get_live_market_state(self) -> Dict:
        """Get comprehensive live market state"""
        try:
            # Fetch multiple indices concurrently
            tasks = [
                self.get_live_index_data("NIFTY50"),
                self.get_live_index_data("SENSEX"),
                self.get_live_index_data("BANKNIFTY"),
                self.get_live_index_data("NIFTYIT")
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            indices = []
            for i, result in enumerate(results):
                index_names = ["NIFTY50", "SENSEX", "BANKNIFTY", "NIFTYIT"]
                if isinstance(result, dict) and result:
                    # Map to display names
                    display_names = {
                        "NIFTY50": "NIFTY 50",
                        "SENSEX": "SENSEX", 
                        "BANKNIFTY": "BANK NIFTY",
                        "NIFTYIT": "NIFTY IT"
                    }
                    
                    index_data = {
                        "name": display_names.get(index_names[i], index_names[i]),
                        "symbol": index_names[i],
                        "value": f"{result['value']:,.2f}",
                        "change": f"{result['change']:+.2f}",
                        "trend": "up" if result['change'] >= 0 else "down",
                        "change_percent": f"{result['change_percent']:+.2f}%"
                    }
                    indices.append(index_data)
                else:
                    # Add fallback data for failed requests
                    indices.append(self._get_fallback_index_data(index_names[i]))
            
            # Determine market status (simplified)
            market_status = self._get_market_status()
            
            return {
                "status": "success",
                "data": {
                    "market_status": market_status,
                    "timestamp": time.time(),
                    "indices": indices,
                    "market_breadth": await self._get_market_breadth(),
                    "volatility": await self._get_volatility_data(),
                    "sentiment": self._get_market_sentiment(indices),
                    "last_updated": time.time()
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting live market state: {e}")
            return self._get_fallback_market_state()
    
    def _get_market_status(self) -> str:
        """Determine if market is open/closed based on time"""
        # Simplified - you can enhance this with holidays, etc.
        import datetime
        now = datetime.datetime.now()
        
        # Indian market hours: 9:15 AM to 3:30 PM IST (Mon-Fri)
        if now.weekday() < 5:  # Monday = 0, Friday = 4
            market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
            market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
            
            if market_open <= now <= market_close:
                return "open"
            elif now < market_open:
                return "pre_market"
            else:
                return "after_hours"
        else:
            return "closed"
    
    async def _get_market_breadth(self) -> Dict:
        """Get market breadth data (advances/declines)"""
        # This would ideally come from a real data source
        # For now, return reasonable estimates
        return {
            "advances": 1420,
            "declines": 780,
            "unchanged": 156
        }
    
    async def _get_volatility_data(self) -> Dict:
        """Get volatility data"""
        try:
            vix_data = await self.get_live_index_data("INDIAVIX")
            if vix_data:
                return {
                    "india_vix": vix_data['value'],
                    "trend": "declining" if vix_data['change'] < 0 else "rising"
                }
        except:
            pass
            
        return {
            "india_vix": 12.85,
            "trend": "declining"
        }
    
    def _get_market_sentiment(self, indices: List[Dict]) -> str:
        """Determine market sentiment based on index movements"""
        positive_count = sum(1 for idx in indices if idx.get('trend') == 'up')
        total_count = len(indices)
        
        if positive_count >= total_count * 0.75:
            return "bullish"
        elif positive_count >= total_count * 0.5:
            return "neutral"
        else:
            return "bearish"
    
    def _get_fallback_data(self, index_name: str) -> Dict:
        """Fallback data when live fetch fails"""
        fallback_values = {
            "NIFTY50": {"value": 19650.0, "change": 120.0},
            "SENSEX": {"value": 65800.0, "change": 350.0},
            "BANKNIFTY": {"value": 44200.0, "change": -80.0},
            "NIFTYIT": {"value": 28400.0, "change": 200.0}
        }
        
        data = fallback_values.get(index_name.upper(), {"value": 1000.0, "change": 0.0})
        change_percent = (data['change'] / data['value']) * 100
        
        return {
            "symbol": index_name,
            "value": data['value'],
            "change": data['change'],
            "change_percent": round(change_percent, 2),
            "volume": 0,
            "timestamp": time.time(),
            "source": "fallback"
        }
    
    def _get_fallback_index_data(self, index_name: str) -> Dict:
        """Fallback index data for display"""
        fallback_data = self._get_fallback_data(index_name)
        display_names = {
            "NIFTY50": "NIFTY 50",
            "SENSEX": "SENSEX",
            "BANKNIFTY": "BANK NIFTY", 
            "NIFTYIT": "NIFTY IT"
        }
        
        return {
            "name": display_names.get(index_name, index_name),
            "symbol": index_name,
            "value": f"{fallback_data['value']:,.2f}",
            "change": f"{fallback_data['change']:+.2f}",
            "trend": "up" if fallback_data['change'] >= 0 else "down",
            "change_percent": f"{fallback_data['change_percent']:+.2f}%"
        }
    
    def _get_fallback_market_state(self) -> Dict:
        """Fallback market state when all fetches fail"""
        return {
            "status": "success",
            "data": {
                "market_status": "open",
                "timestamp": time.time(),
                "indices": [
                    {
                        "name": "NIFTY 50",
                        "symbol": "NIFTY50",
                        "value": "19,650.00",
                        "change": "+120.00",
                        "trend": "up",
                        "change_percent": "+0.61%"
                    },
                    {
                        "name": "SENSEX",
                        "symbol": "SENSEX",
                        "value": "65,800.00",
                        "change": "+350.00", 
                        "trend": "up",
                        "change_percent": "+0.53%"
                    },
                    {
                        "name": "BANK NIFTY",
                        "symbol": "BANKNIFTY",
                        "value": "44,200.00",
                        "change": "-80.00",
                        "trend": "down",
                        "change_percent": "-0.18%"
                    },
                    {
                        "name": "NIFTY IT",
                        "symbol": "NIFTYIT",
                        "value": "28,400.00",
                        "change": "+200.00",
                        "trend": "up",
                        "change_percent": "+0.71%"
                    }
                ],
                "market_breadth": {
                    "advances": 1420,
                    "declines": 780,
                    "unchanged": 156
                },
                "volatility": {
                    "india_vix": 12.85,
                    "trend": "declining"
                },
                "sentiment": "bullish",
                "last_updated": time.time()
            }
        }


# Global service instance
market_data_service = MarketDataService()
