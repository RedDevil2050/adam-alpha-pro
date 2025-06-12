"""
Advanced Quad-Channel Stealth Agent Base with Background Data Collection
========================================================================

This enhanced base class provides:
- Quad-channel data collection (Primary, Secondary, Tertiary, Emergency)
- Continuous background data streaming
- Advanced caching with Redis
- Circuit breaker patterns
- Real-time performance monitoring
- Intelligent data fusion algorithms
- Adaptive retry mechanisms
"""

import asyncio
import time
import redis
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple, Union, AsyncGenerator
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from loguru import logger
from concurrent.futures import ThreadPoolExecutor
import httpx
import yfinance as yf
from backend.utils.cache_utils import get_redis_client
from backend.monitor.tracker import AGENT_EXECUTION_COUNT, DATA_PROVIDER_CALLS, ACTIVE_USERS

@dataclass
class DataChannelConfig:
    """Configuration for each data channel"""
    name: str
    timeout: int
    max_retries: int
    priority: int  # 1=highest, 4=lowest
    circuit_breaker_threshold: int = 5
    rate_limit_per_minute: int = 60

@dataclass
class QuadChannelData:
    """Container for quad-channel data collection results"""
    primary: Optional[Dict] = None
    secondary: Optional[Dict] = None
    tertiary: Optional[Dict] = None
    emergency: Optional[Dict] = None
    fusion_confidence: float = 0.0
    validation_score: float = 0.0
    collection_timestamp: float = 0.0
    channels_used: List[str] = None

class CircuitBreaker:
    """Circuit breaker implementation for fault tolerance"""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def can_execute(self) -> bool:
        if self.state == "CLOSED":
            return True
        elif self.state == "OPEN":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        else:  # HALF_OPEN
            return True
    
    def record_success(self):
        self.failure_count = 0
        self.state = "CLOSED"
    
    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"

class AdvancedStealthAgentBase(ABC):
    """
    Next-generation stealth agent base with quad-channel architecture
    and continuous background data collection capabilities.
    """
    
    def __init__(self):
        # Channel configurations
        self.channels = {
            "primary": DataChannelConfig("primary", timeout=8, max_retries=3, priority=1),
            "secondary": DataChannelConfig("secondary", timeout=12, max_retries=2, priority=2),
            "tertiary": DataChannelConfig("tertiary", timeout=15, max_retries=2, priority=3),
            "emergency": DataChannelConfig("emergency", timeout=20, max_retries=1, priority=4)
        }
        
        # Circuit breakers for each channel
        self.circuit_breakers = {
            channel: CircuitBreaker() for channel in self.channels.keys()
        }
        
        # Background collection settings
        self.background_enabled = False
        self.background_symbols = set()
        self.collection_interval = 30  # seconds
        self.background_tasks = {}
        
        # Performance tracking
        self.performance_metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "avg_response_time": 0.0,
            "channels_performance": {ch: {"success": 0, "failure": 0} for ch in self.channels.keys()}
        }
        
        # Data fusion settings
        self.fusion_weights = {"primary": 0.4, "secondary": 0.3, "tertiary": 0.2, "emergency": 0.1}
        self.validation_threshold = 0.7
        
        # Cache settings
        self.cache_ttl = {
            "primary": 60,      # 1 minute for primary data
            "secondary": 120,   # 2 minutes for secondary
            "tertiary": 300,    # 5 minutes for tertiary
            "emergency": 600    # 10 minutes for emergency
        }
        
        # User agents for stealth mode
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0"
        ]
        
        # Initialize Redis client for caching
        try:
            self.redis_client = get_redis_client()
        except Exception as e:
            logger.warning(f"Redis unavailable, using in-memory cache: {e}")
            self.redis_client = None
            self.memory_cache = {}
    
    async def execute(self, symbol: str, agent_outputs: dict = {}) -> dict:
        """Execute quad-channel stealth agent logic with advanced data fusion."""
        start_time = time.time()
        logger.info(f"🚀 Starting quad-channel analysis for {symbol} using {self.__class__.__name__}")
        
        try:
            # Attempt quad-channel data collection
            quad_data = await self._quad_channel_fetch(symbol)
            
            # Validate and fuse data from all channels
            fused_data = await self._intelligent_data_fusion(quad_data, symbol)
            
            if not fused_data or fused_data.validation_score < self.validation_threshold:
                return self._error_response(symbol, "Insufficient data quality from all channels")
            
            # Execute agent-specific analysis with fused data
            result = await self._execute_analysis(symbol, agent_outputs, fused_data)
            
            # Enhance result with quad-channel metadata
            result = self._enhance_with_quad_metadata(result, quad_data)
            
            # Update performance metrics
            self._update_performance_metrics(True, time.time() - start_time)
            
            logger.success(f"✅ Quad-channel analysis completed for {symbol} in {time.time() - start_time:.2f}s")
            return result
            
        except Exception as e:
            self._update_performance_metrics(False, time.time() - start_time)
            logger.error(f"❌ Quad-channel analysis failed for {symbol}: {e}")
            return self._error_response(symbol, f"Analysis failed: {str(e)}")
    
    async def _quad_channel_fetch(self, symbol: str) -> QuadChannelData:
        """
        Fetch data from all four channels concurrently with intelligent prioritization.
        """
        logger.debug(f"🌐 Starting quad-channel fetch for {symbol}")
        
        # Create tasks for all channels
        tasks = {}
        for channel_name, config in self.channels.items():
            if self.circuit_breakers[channel_name].can_execute():
                tasks[channel_name] = asyncio.create_task(
                    self._fetch_channel_with_circuit_breaker(symbol, channel_name, config)
                )
            else:
                logger.warning(f"⚡ Circuit breaker OPEN for {channel_name} channel")
        
        # Execute all channels concurrently with individual timeouts
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        
        # Map results back to channels
        quad_data = QuadChannelData(
            channels_used=[],
            collection_timestamp=time.time()
        )
        
        for i, (channel_name, task) in enumerate(tasks.items()):
            result = results[i]
            
            if isinstance(result, Exception):
                logger.warning(f"⚠️ {channel_name} channel failed: {result}")
                self.circuit_breakers[channel_name].record_failure()
                self.performance_metrics["channels_performance"][channel_name]["failure"] += 1
            else:
                logger.debug(f"✅ {channel_name} channel successful")
                setattr(quad_data, channel_name, result)
                quad_data.channels_used.append(channel_name)
                self.circuit_breakers[channel_name].record_success()
                self.performance_metrics["channels_performance"][channel_name]["success"] += 1
        
        logger.info(f"📊 Quad-channel fetch completed: {len(quad_data.channels_used)}/4 channels successful")
        return quad_data
    
    async def _fetch_channel_with_circuit_breaker(self, symbol: str, channel: str, config: DataChannelConfig) -> Optional[Dict]:
        """Fetch data from a specific channel with circuit breaker protection."""
        
        # Check cache first
        cached_data = await self._get_cached_data(symbol, channel)
        if cached_data:
            logger.debug(f"📋 Cache hit for {symbol} on {channel} channel")
            return cached_data
        
        # Attempt fetch with retries
        for attempt in range(config.max_retries + 1):
            try:
                logger.debug(f"🎯 {channel} fetch attempt {attempt + 1} for {symbol}")
                
                # Route to appropriate fetch method
                if channel == "primary":
                    data = await self._fetch_primary_source(symbol)
                elif channel == "secondary":
                    data = await self._fetch_secondary_source(symbol)
                elif channel == "tertiary":
                    data = await self._fetch_tertiary_source(symbol)
                elif channel == "emergency":
                    data = await self._fetch_emergency_source(symbol)
                else:
                    raise ValueError(f"Unknown channel: {channel}")
                
                if data:
                    # Cache successful result
                    await self._cache_data(symbol, channel, data, self.cache_ttl[channel])
                    return {**data, "source": channel, "attempt": attempt + 1, "timestamp": time.time()}
                    
            except Exception as e:
                logger.warning(f"⚠️ {channel} fetch attempt {attempt + 1} failed for {symbol}: {e}")
                if attempt < config.max_retries:
                    await asyncio.sleep(1 * (attempt + 1))  # Exponential backoff
        
        logger.error(f"❌ {channel} fetch exhausted retries for {symbol}")
        return None
    
    async def _intelligent_data_fusion(self, quad_data: QuadChannelData, symbol: str) -> Optional[QuadChannelData]:
        """
        Intelligently fuse data from multiple channels using advanced algorithms.
        """
        logger.debug(f"🔬 Starting intelligent data fusion for {symbol}")
        
        if not quad_data.channels_used:
            return None
        
        # Calculate fusion confidence based on channel availability and quality
        fusion_confidence = 0.0
        available_channels = []
        
        for channel in ["primary", "secondary", "tertiary", "emergency"]:
            channel_data = getattr(quad_data, channel)
            if channel_data:
                available_channels.append(channel)
                fusion_confidence += self.fusion_weights[channel]
        
        # Cross-validate data between channels
        validation_score = await self._cross_validate_channels(quad_data, symbol)
        
        quad_data.fusion_confidence = fusion_confidence
        quad_data.validation_score = validation_score
        
        logger.success(f"✅ Data fusion completed: confidence={fusion_confidence:.2f}, validation={validation_score:.2f}")
        return quad_data
    
    async def _cross_validate_channels(self, quad_data: QuadChannelData, symbol: str) -> float:
        """Cross-validate data consistency across channels."""
        
        # Collect price data from all available channels
        prices = []
        for channel in ["primary", "secondary", "tertiary", "emergency"]:
            channel_data = getattr(quad_data, channel)
            if channel_data and "price" in channel_data:
                prices.append(channel_data["price"])
        
        if len(prices) < 2:
            return 0.5  # Not enough data for cross-validation
        
        # Calculate price variance
        avg_price = sum(prices) / len(prices)
        max_deviation = max(abs(p - avg_price) / avg_price for p in prices) * 100
        
        # Score based on price consistency (lower deviation = higher score)
        if max_deviation < 1:    # < 1% deviation
            return 0.9
        elif max_deviation < 3:  # < 3% deviation
            return 0.8
        elif max_deviation < 5:  # < 5% deviation
            return 0.7
        elif max_deviation < 10: # < 10% deviation
            return 0.6
        else:
            return 0.3  # High deviation, low confidence
    
    # === Background Data Collection System ===
    
    async def start_background_collection(self, symbols: List[str], interval: int = 30):
        """Start continuous background data collection for specified symbols."""
        
        logger.info(f"🔄 Starting background collection for {len(symbols)} symbols (interval: {interval}s)")
        self.background_enabled = True
        self.background_symbols.update(symbols)
        self.collection_interval = interval
        
        for symbol in symbols:
            if symbol not in self.background_tasks:
                task = asyncio.create_task(self._background_collection_loop(symbol))
                self.background_tasks[symbol] = task
                logger.debug(f"📡 Started background task for {symbol}")
    
    async def stop_background_collection(self, symbols: List[str] = None):
        """Stop background collection for specified symbols or all symbols."""
        
        symbols_to_stop = symbols or list(self.background_symbols)
        logger.info(f"⏹️ Stopping background collection for {len(symbols_to_stop)} symbols")
        
        for symbol in symbols_to_stop:
            if symbol in self.background_tasks:
                self.background_tasks[symbol].cancel()
                del self.background_tasks[symbol]
                self.background_symbols.discard(symbol)
                logger.debug(f"🔴 Stopped background task for {symbol}")
        
        if not self.background_symbols:
            self.background_enabled = False
    
    async def _background_collection_loop(self, symbol: str):
        """Continuous data collection loop for a single symbol."""
        
        logger.debug(f"🔁 Background collection loop started for {symbol}")
        
        while self.background_enabled and symbol in self.background_symbols:
            try:
                start_time = time.time()
                
                # Perform quad-channel data collection
                quad_data = await self._quad_channel_fetch(symbol)
                fused_data = await self._intelligent_data_fusion(quad_data, symbol)
                
                if fused_data and fused_data.validation_score >= self.validation_threshold:
                    # Store in background cache with extended TTL
                    await self._cache_background_data(symbol, fused_data)
                    
                    # Emit real-time data event
                    await self._emit_realtime_data(symbol, fused_data)
                
                collection_time = time.time() - start_time
                logger.debug(f"📊 Background collection for {symbol} completed in {collection_time:.2f}s")
                
                # Dynamic interval adjustment based on performance
                sleep_time = max(self.collection_interval - collection_time, 5)
                await asyncio.sleep(sleep_time)
                
            except asyncio.CancelledError:
                logger.info(f"🛑 Background collection cancelled for {symbol}")
                break
            except Exception as e:
                logger.error(f"❌ Background collection error for {symbol}: {e}")
                await asyncio.sleep(30)  # Wait before retry
    
    async def _emit_realtime_data(self, symbol: str, fused_data: QuadChannelData):
        """Emit real-time data updates for streaming consumers."""
        
        realtime_event = {
            "type": "stealth_data_update",
            "symbol": symbol,
            "timestamp": fused_data.collection_timestamp,
            "confidence": fused_data.fusion_confidence,
            "validation_score": fused_data.validation_score,
            "channels_used": fused_data.channels_used,
            "data_summary": self._create_data_summary(fused_data)
        }
        
        # Here you could publish to a message queue, WebSocket, etc.
        logger.debug(f"📢 Real-time data emitted for {symbol}")
    
    def _create_data_summary(self, fused_data: QuadChannelData) -> Dict:
        """Create a summary of the fused data for real-time streaming."""
        
        summary = {
            "price": None,
            "volume": None,
            "market_cap": None,
            "data_freshness": time.time() - fused_data.collection_timestamp
        }
        
        # Extract key metrics from available channels
        for channel in ["primary", "secondary", "tertiary", "emergency"]:
            channel_data = getattr(fused_data, channel)
            if channel_data:
                summary["price"] = summary["price"] or channel_data.get("price")
                summary["volume"] = summary["volume"] or channel_data.get("volume")
                summary["market_cap"] = summary["market_cap"] or channel_data.get("market_cap")
        
        return summary
    
    # === Data Channel Implementations ===
    
    @abstractmethod
    async def _fetch_primary_source(self, symbol: str) -> Optional[Dict]:
        """Fetch data from primary source (stealth scraping). Implement in subclasses."""
        raise NotImplementedError("Subclasses must implement _fetch_primary_source")
    
    async def _fetch_secondary_source(self, symbol: str) -> Optional[Dict]:
        """Fetch data from secondary source (Yahoo Finance API)."""
        try:
            yahoo_symbol = self._normalize_symbol_for_yahoo(symbol)
            data = await asyncio.get_event_loop().run_in_executor(
                None, self._get_yahoo_data, yahoo_symbol, symbol
            )
            return {**data, "source": "yahoo_finance"}
        except Exception as e:
            logger.warning(f"Yahoo Finance fetch failed for {symbol}: {e}")
            return None
    
    async def _fetch_tertiary_source(self, symbol: str) -> Optional[Dict]:
        """Fetch data from tertiary source (Alpha Vantage API)."""
        try:
            # Implement Alpha Vantage API call
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(
                    f"https://www.alphavantage.co/query",
                    params={
                        "function": "GLOBAL_QUOTE",
                        "symbol": f"{symbol}.BSE",
                        "apikey": "demo"  # Replace with actual API key
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    quote = data.get("Global Quote", {})
                    
                    return {
                        "price": float(quote.get("05. price", 0)),
                        "volume": int(quote.get("06. volume", 0)),
                        "change_percent": quote.get("10. change percent", "0%"),
                        "source": "alpha_vantage"
                    }
        except Exception as e:
            logger.warning(f"Alpha Vantage fetch failed for {symbol}: {e}")
            return None
    
    async def _fetch_emergency_source(self, symbol: str) -> Optional[Dict]:
        """Fetch data from emergency source (Polygon.io API)."""
        try:
            # Implement Polygon.io API call as emergency backup
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.get(
                    f"https://api.polygon.io/v2/last/nbbo/{symbol}",
                    params={"apikey": "demo"}  # Replace with actual API key
                )
                
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", {})
                    
                    return {
                        "price": results.get("P", 0),  # Ask price
                        "bid": results.get("p", 0),    # Bid price
                        "timestamp": results.get("t", 0),
                        "source": "polygon_io"
                    }
        except Exception as e:
            logger.warning(f"Polygon.io fetch failed for {symbol}: {e}")
            return None
    
    # === Caching System ===
    
    async def _get_cached_data(self, symbol: str, channel: str) -> Optional[Dict]:
        """Retrieve cached data for symbol and channel."""
        cache_key = f"stealth:{symbol}:{channel}"
        
        try:
            if self.redis_client:
                cached = await asyncio.get_event_loop().run_in_executor(
                    None, self.redis_client.get, cache_key
                )
                if cached:
                    return json.loads(cached)
            else:
                # Use in-memory cache
                if cache_key in self.memory_cache:
                    cache_entry = self.memory_cache[cache_key]
                    if time.time() - cache_entry["timestamp"] < cache_entry["ttl"]:
                        return cache_entry["data"]
                    else:
                        del self.memory_cache[cache_key]
        except Exception as e:
            logger.warning(f"Cache retrieval error: {e}")
        
        return None
    
    async def _cache_data(self, symbol: str, channel: str, data: Dict, ttl: int):
        """Cache data for symbol and channel."""
        cache_key = f"stealth:{symbol}:{channel}"
        
        try:
            if self.redis_client:
                await asyncio.get_event_loop().run_in_executor(
                    None, self.redis_client.setex, cache_key, ttl, json.dumps(data)
                )
            else:
                # Use in-memory cache
                self.memory_cache[cache_key] = {
                    "data": data,
                    "timestamp": time.time(),
                    "ttl": ttl
                }
        except Exception as e:
            logger.warning(f"Cache storage error: {e}")
    
    async def _cache_background_data(self, symbol: str, fused_data: QuadChannelData):
        """Cache background collected data with extended TTL."""
        cache_key = f"stealth:background:{symbol}"
        cache_data = {
            "fused_data": asdict(fused_data),
            "collection_time": fused_data.collection_timestamp
        }
        
        try:
            if self.redis_client:
                await asyncio.get_event_loop().run_in_executor(
                    None, self.redis_client.setex, cache_key, 1800, json.dumps(cache_data)  # 30 min TTL
                )
        except Exception as e:
            logger.warning(f"Background cache storage error: {e}")
    
    # === Utility Methods ===
    
    def _normalize_symbol_for_yahoo(self, symbol: str) -> str:
        """Normalize symbol for Yahoo Finance API."""
        if symbol.endswith('.NS') or symbol.endswith('.BO'):
            return symbol
        return f"{symbol}.NS"  # Default to NSE
    
    def _get_yahoo_data(self, yahoo_symbol: str, symbol: str) -> Dict:
        """Get Yahoo Finance data synchronously."""
        try:
            ticker = yf.Ticker(yahoo_symbol)
            info = ticker.info
            hist = ticker.history(period="1d")
            
            return {
                "price": float(hist['Close'].iloc[-1]) if not hist.empty else info.get('currentPrice', 0),
                "volume": int(hist['Volume'].iloc[-1]) if not hist.empty else info.get('volume', 0),
                "market_cap": info.get('marketCap', 0),
                "pe_ratio": info.get('trailingPE', 0),
                "company_name": info.get('longName', symbol),
                "yahoo_symbol": yahoo_symbol
            }
        except Exception as e:
            logger.warning(f"Yahoo Finance data error: {e}")
            return {"yahoo_symbol": yahoo_symbol, "error": str(e)}
    
    def _update_performance_metrics(self, success: bool, response_time: float):
        """Update performance tracking metrics."""
        self.performance_metrics["total_requests"] += 1
        
        if success:
            self.performance_metrics["successful_requests"] += 1
        else:
            self.performance_metrics["failed_requests"] += 1
        
        # Update average response time
        total = self.performance_metrics["total_requests"]
        current_avg = self.performance_metrics["avg_response_time"]
        self.performance_metrics["avg_response_time"] = (current_avg * (total - 1) + response_time) / total
    
    def get_performance_report(self) -> Dict:
        """Get comprehensive performance report."""
        total = self.performance_metrics["total_requests"]
        success_rate = (self.performance_metrics["successful_requests"] / total * 100) if total > 0 else 0
        
        return {
            "agent_class": self.__class__.__name__,
            "total_requests": total,
            "success_rate": f"{success_rate:.1f}%",
            "avg_response_time": f"{self.performance_metrics['avg_response_time']:.2f}s",
            "channels_performance": self.performance_metrics["channels_performance"],
            "background_collection": {
                "enabled": self.background_enabled,
                "active_symbols": len(self.background_symbols),
                "active_tasks": len(self.background_tasks)
            },
            "circuit_breaker_status": {
                channel: breaker.state 
                for channel, breaker in self.circuit_breakers.items()
            }
        }
    
    def _enhance_with_quad_metadata(self, result: Dict, quad_data: QuadChannelData) -> Dict:
        """Enhance analysis result with quad-channel metadata."""
        if not isinstance(result, dict):
            return result
        
        if "details" not in result:
            result["details"] = {}
        
        result["details"]["quad_channel_info"] = {
            "channels_used": quad_data.channels_used,
            "fusion_confidence": quad_data.fusion_confidence,
            "validation_score": quad_data.validation_score,
            "collection_timestamp": quad_data.collection_timestamp,
            "data_freshness": time.time() - quad_data.collection_timestamp,
            "channel_availability": {
                channel: getattr(quad_data, channel) is not None
                for channel in ["primary", "secondary", "tertiary", "emergency"]
            }
        }
        
        # Boost confidence based on quad-channel performance
        if result.get("confidence") and quad_data.fusion_confidence > 0.8:
            original_confidence = result["confidence"]
            result["confidence"] = min(original_confidence * (1 + quad_data.fusion_confidence * 0.2), 1.0)
            result["details"]["quad_channel_info"]["confidence_boost"] = True
        
        return result
    
    @abstractmethod
    async def _execute_analysis(self, symbol: str, agent_outputs: dict, fused_data: QuadChannelData) -> Dict:
        """Execute agent-specific analysis logic. Must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement _execute_analysis method")
    
    def _error_response(self, symbol: str, error_message: str) -> dict:
        """Standard error response format for stealth agents."""
        agent_name = getattr(self, 'agent_name', self.__class__.__name__.lower())
        
        return {
            "symbol": symbol,
            "verdict": "ERROR",
            "confidence": 0.0,
            "value": 0.0,
            "details": {
                "error_message": error_message,
                "timestamp": time.time(),
                "agent_performance": self.get_performance_report()
            },
            "error": error_message,
            "agent_name": agent_name
        }
