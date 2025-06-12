"""
Stealth Agent Enhancement Framework
==================================

Comprehensive improvements for stealth agents to achieve higher reliability,
better performance, and enhanced resilience.
"""

import asyncio
import time
import random
import aiohttp
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from loguru import logger

# === 1. ADAPTIVE RATE LIMITING SYSTEM ===

@dataclass
class RateLimitTracker:
    """Track rate limits and adapt requests dynamically"""
    requests_per_minute: int = 60
    current_requests: int = 0
    reset_time: float = 0
    backoff_multiplier: float = 1.0
    consecutive_failures: int = 0
    
class AdaptiveRateLimiter:
    """Intelligent rate limiter that adapts to API responses"""
    
    def __init__(self):
        self.trackers = {}
        
    async def wait_if_needed(self, source: str):
        """Wait if rate limit would be exceeded"""
        if source not in self.trackers:
            self.trackers[source] = RateLimitTracker()
            
        tracker = self.trackers[source]
        
        # Reset counter if a minute has passed
        if time.time() > tracker.reset_time:
            tracker.current_requests = 0
            tracker.reset_time = time.time() + 60
            
        # Check if we need to wait
        if tracker.current_requests >= tracker.requests_per_minute:
            wait_time = tracker.reset_time - time.time()
            if wait_time > 0:
                logger.info(f"⏳ Rate limit reached for {source}, waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)
                tracker.current_requests = 0
                tracker.reset_time = time.time() + 60
                
        tracker.current_requests += 1
        
    def record_rate_limit_hit(self, source: str):
        """Record when we hit a rate limit to adapt future requests"""
        if source in self.trackers:
            tracker = self.trackers[source]
            tracker.requests_per_minute = max(10, int(tracker.requests_per_minute * 0.7))
            tracker.backoff_multiplier = min(3.0, tracker.backoff_multiplier * 1.5)
            logger.warning(f"🐌 Reduced rate limit for {source} to {tracker.requests_per_minute}/min")

# === 2. SMART URL RESOLUTION ===

class URLResolver:
    """Intelligent URL resolution with fallback patterns"""
    
    URL_PATTERNS = {
        'trendlyne': [
            'https://trendlyne.com/equity/{symbol}/',
            'https://www.trendlyne.com/equity/{symbol}',
            'https://trendlyne.com/stocks/{symbol}',
            'https://www.trendlyne.com/stocks/{symbol}/',
            'https://trendlyne.com/equity/{symbol}.NSE',
            'https://trendlyne.com/equity/{symbol}.BSE'
        ],
        'tickertape': [
            'https://www.tickertape.in/stocks/{symbol}',
            'https://tickertape.in/stocks/{symbol}',
            'https://www.tickertape.in/stocks/{symbol_lower}',
            'https://tickertape.in/equity/{symbol}',
            'https://www.tickertape.in/equity/{symbol_lower}'
        ],
        'tijori': [
            'https://tijori.com/stock/{symbol}',
            'https://www.tijori.com/stocks/{symbol}',
            'https://tijori.com/equity/{symbol}',
            'https://www.tijori.com/equity/{symbol}',
            'https://tijori.com/stocks/{symbol_lower}',
            'https://tijori.com/nse/{symbol}'
        ],
        'stockedge': [
            'https://web.stockedge.com/share/{symbol}/NSE',
            'https://stockedge.com/share/{symbol}/NSE',
            'https://web.stockedge.com/stock/{symbol}',
            'https://web.stockedge.com/equity/{symbol}',
            'https://web.stockedge.com/share/{symbol}/BSE'
        ],
        'tradingview': [
            'https://www.tradingview.com/symbols/NSE-{symbol}/',
            'https://tradingview.com/symbols/NSE-{symbol}',
            'https://www.tradingview.com/symbols/BSE-{symbol}/',
            'https://in.tradingview.com/symbols/NSE-{symbol}/',
            'https://www.tradingview.com/chart/NSE:{symbol}/'
        ]
    }
    
    @classmethod
    async def find_working_url(cls, source: str, symbol: str, session: aiohttp.ClientSession) -> Optional[str]:
        """Find the first working URL for a source and symbol"""
        if source not in cls.URL_PATTERNS:
            return None
            
        symbol_variants = {
            'symbol': symbol,
            'symbol_lower': symbol.lower()
        }
        
        for url_pattern in cls.URL_PATTERNS[source]:
            try:
                url = url_pattern.format(**symbol_variants)
                async with session.head(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status in [200, 301, 302]:
                        logger.debug(f"✅ Found working URL for {source}: {url}")
                        return url
            except Exception as e:
                logger.debug(f"❌ URL failed for {source}: {url} - {e}")
                continue
                
        logger.warning(f"⚠️ No working URL found for {source}:{symbol}")
        return None

# === 3. ENHANCED ERROR HANDLING ===

class ErrorClassifier:
    """Classify and handle different types of errors intelligently"""
    
    RETRYABLE_ERRORS = {
        'rate_limit': ['429', 'rate limit', 'too many requests'],
        'server_error': ['500', '502', '503', '504'],
        'timeout': ['timeout', 'connection timeout'],
        'network': ['connection error', 'network error', 'dns']
    }
    
    @classmethod
    def classify_error(cls, error: Exception, status_code: int = None) -> str:
        """Classify error type for appropriate handling"""
        error_str = str(error).lower()
        
        if status_code:
            if status_code == 429:
                return 'rate_limit'
            elif status_code >= 500:
                return 'server_error'
            elif status_code == 404:
                return 'not_found'
            elif status_code == 401:
                return 'auth_error'
                
        for error_type, keywords in cls.RETRYABLE_ERRORS.items():
            if any(keyword in error_str for keyword in keywords):
                return error_type
                
        return 'unknown'
    
    @classmethod
    def get_retry_strategy(cls, error_type: str, attempt: int) -> Dict[str, Any]:
        """Get retry strategy based on error type"""
        strategies = {
            'rate_limit': {
                'retry': True,
                'delay': min(60 * (2 ** attempt), 300),  # Exponential backoff, max 5 min
                'max_attempts': 3
            },
            'server_error': {
                'retry': True,
                'delay': min(5 * (2 ** attempt), 60),  # Quick retry for server errors
                'max_attempts': 4
            },
            'timeout': {
                'retry': True,
                'delay': 2 * attempt,
                'max_attempts': 3
            },
            'not_found': {
                'retry': False,  # Don't retry 404s
                'delay': 0,
                'max_attempts': 0
            },
            'auth_error': {
                'retry': False,  # Don't retry auth errors
                'delay': 0,
                'max_attempts': 0
            }
        }
        
        return strategies.get(error_type, {
            'retry': True,
            'delay': 5 * attempt,
            'max_attempts': 2
        })

# === 4. INTELLIGENT DATA VALIDATION ===

class DataValidator:
    """Advanced data validation with Indian market specifics"""
    
    INDIAN_STOCK_RANGES = {
        'RELIANCE': {'min': 2000, 'max': 3000},
        'TCS': {'min': 3000, 'max': 4500},
        'INFY': {'min': 1500, 'max': 2200},
        'HDFCBANK': {'min': 1400, 'max': 1800},
        'ICICIBANK': {'min': 800, 'max': 1200},
        'SBIN': {'min': 500, 'max': 800},
        'BHARTIARTL': {'min': 800, 'max': 1200},
        'ITC': {'min': 350, 'max': 500},
        'HINDUNILVR': {'min': 2200, 'max': 2800},
        'KOTAKBANK': {'min': 1600, 'max': 2200}
    }
    
    @classmethod
    def validate_price_data(cls, symbol: str, price: float, volume: int = None) -> Dict[str, Any]:
        """Validate price data against known ranges and patterns"""
        validation_result = {
            'is_valid': True,
            'confidence': 1.0,
            'issues': [],
            'adjustments': {}
        }
        
        # Basic price validation
        if not price or price <= 0:
            validation_result['is_valid'] = False
            validation_result['issues'].append('Invalid price value')
            return validation_result
            
        # Symbol-specific validation
        if symbol in cls.INDIAN_STOCK_RANGES:
            range_info = cls.INDIAN_STOCK_RANGES[symbol]
            if price < range_info['min'] * 0.5 or price > range_info['max'] * 2:
                validation_result['confidence'] = 0.3
                validation_result['issues'].append(f'Price {price} outside expected range')
                
        # Volume validation
        if volume is not None:
            if volume < 0:
                validation_result['is_valid'] = False
                validation_result['issues'].append('Negative volume')
            elif volume == 0:
                validation_result['confidence'] *= 0.8
                validation_result['issues'].append('Zero volume')
                
        return validation_result

# === 5. PERFORMANCE OPTIMIZATION ===

class PerformanceOptimizer:
    """Optimize agent performance based on historical data"""
    
    def __init__(self):
        self.channel_performance = {}
        self.symbol_performance = {}
        
    def record_performance(self, channel: str, symbol: str, success: bool, response_time: float):
        """Record performance metrics"""
        if channel not in self.channel_performance:
            self.channel_performance[channel] = {
                'success_count': 0,
                'failure_count': 0,
                'avg_response_time': 0,
                'total_requests': 0
            }
            
        metrics = self.channel_performance[channel]
        metrics['total_requests'] += 1
        
        if success:
            metrics['success_count'] += 1
        else:
            metrics['failure_count'] += 1
            
        # Update average response time
        metrics['avg_response_time'] = (
            (metrics['avg_response_time'] * (metrics['total_requests'] - 1) + response_time) 
            / metrics['total_requests']
        )
        
    def get_channel_priority(self, symbol: str) -> List[str]:
        """Get optimized channel priority based on performance"""
        channels = ['primary', 'secondary', 'tertiary', 'emergency']
        
        # Sort by success rate and response time
        def channel_score(channel):
            if channel not in self.channel_performance:
                return 0.5  # Default score for unknown channels
                
            metrics = self.channel_performance[channel]
            if metrics['total_requests'] == 0:
                return 0.5
                
            success_rate = metrics['success_count'] / metrics['total_requests']
            response_score = max(0, 1 - (metrics['avg_response_time'] / 30))  # Normalize to 30s max
            
            return (success_rate * 0.7) + (response_score * 0.3)
            
        return sorted(channels, key=channel_score, reverse=True)

# === 6. FALLBACK DATA GENERATION ===

class FallbackDataGenerator:
    """Generate realistic fallback data when all sources fail"""
    
    MARKET_PATTERNS = {
        'morning': {'volatility': 1.2, 'volume_multiplier': 1.5},
        'midday': {'volatility': 0.8, 'volume_multiplier': 0.7},
        'evening': {'volatility': 1.1, 'volume_multiplier': 1.3}
    }
    
    @classmethod
    def generate_realistic_data(cls, symbol: str, last_known_price: float = None) -> Dict[str, Any]:
        """Generate realistic market data as last resort"""
        import datetime
        
        # Base prices for major Indian stocks
        base_prices = {
            'RELIANCE': 2500, 'TCS': 3500, 'INFY': 1800, 'HDFCBANK': 1600,
            'ICICIBANK': 1000, 'SBIN': 650, 'BHARTIARTL': 1000, 'ITC': 425,
            'HINDUNILVR': 2500, 'KOTAKBANK': 1900
        }
        
        base_price = last_known_price or base_prices.get(symbol, 1000)
        
        # Add realistic volatility based on time of day
        current_hour = datetime.datetime.now().hour
        if 9 <= current_hour <= 11:
            pattern = cls.MARKET_PATTERNS['morning']
        elif 11 < current_hour <= 14:
            pattern = cls.MARKET_PATTERNS['midday']
        else:
            pattern = cls.MARKET_PATTERNS['evening']
            
        # Generate price with realistic movement
        price_change = random.uniform(-0.03, 0.03) * pattern['volatility']
        current_price = base_price * (1 + price_change)
        
        # Generate volume
        base_volume = random.randint(100000, 1000000)
        volume = int(base_volume * pattern['volume_multiplier'])
        
        return {
            'price': round(current_price, 2),
            'volume': volume,
            'change': round(current_price - base_price, 2),
            'change_percent': round(price_change * 100, 2),
            'source': 'fallback_generator',
            'confidence': 0.3,  # Low confidence for generated data
            'timestamp': time.time(),
            'market_cap': current_price * random.randint(1000000, 10000000),
            'pe_ratio': round(random.uniform(15, 35), 2)
        }

# === 7. ENHANCED MONITORING ===

class EnhancedMonitor:
    """Comprehensive monitoring for stealth agents"""
    
    def __init__(self):
        self.metrics = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'avg_response_time': 0,
            'channel_health': {},
            'error_patterns': {},
            'performance_trends': []
        }
        
    def record_request(self, channel: str, success: bool, response_time: float, error_type: str = None):
        """Record detailed request metrics"""
        self.metrics['total_requests'] += 1
        
        if success:
            self.metrics['successful_requests'] += 1
        else:
            self.metrics['failed_requests'] += 1
            if error_type:
                if error_type not in self.metrics['error_patterns']:
                    self.metrics['error_patterns'][error_type] = 0
                self.metrics['error_patterns'][error_type] += 1
                
        # Update average response time
        total = self.metrics['total_requests']
        self.metrics['avg_response_time'] = (
            (self.metrics['avg_response_time'] * (total - 1) + response_time) / total
        )
        
        # Update channel health
        if channel not in self.metrics['channel_health']:
            self.metrics['channel_health'][channel] = {
                'success_rate': 0,
                'avg_response_time': 0,
                'last_success': None,
                'consecutive_failures': 0
            }
            
        channel_health = self.metrics['channel_health'][channel]
        if success:
            channel_health['last_success'] = time.time()
            channel_health['consecutive_failures'] = 0
        else:
            channel_health['consecutive_failures'] += 1
            
    def get_health_report(self) -> Dict[str, Any]:
        """Get comprehensive health report"""
        if self.metrics['total_requests'] == 0:
            return {'status': 'No data', 'overall_health': 0}
            
        success_rate = self.metrics['successful_requests'] / self.metrics['total_requests']
        overall_health = min(success_rate * 100, 100)
        
        return {
            'status': 'Healthy' if overall_health > 70 else 'Degraded' if overall_health > 40 else 'Critical',
            'overall_health': overall_health,
            'success_rate': success_rate,
            'avg_response_time': self.metrics['avg_response_time'],
            'total_requests': self.metrics['total_requests'],
            'error_patterns': self.metrics['error_patterns'],
            'channel_health': self.metrics['channel_health']
        }

# === USAGE EXAMPLE ===

class EnhancedStealthAgent:
    """Example of enhanced stealth agent using all improvements"""
    
    def __init__(self):
        self.rate_limiter = AdaptiveRateLimiter()
        self.url_resolver = URLResolver()
        self.error_classifier = ErrorClassifier()
        self.data_validator = DataValidator()
        self.performance_optimizer = PerformanceOptimizer()
        self.fallback_generator = FallbackDataGenerator()
        self.monitor = EnhancedMonitor()
        
    async def fetch_data_enhanced(self, symbol: str, source: str) -> Optional[Dict[str, Any]]:
        """Enhanced data fetching with all improvements"""
        start_time = time.time()
        
        try:
            # Wait for rate limiting
            await self.rate_limiter.wait_if_needed(source)
            
            # Find working URL
            async with aiohttp.ClientSession() as session:
                url = await self.url_resolver.find_working_url(source, symbol, session)
                if not url:
                    return None
                    
                # Fetch data with error handling
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()  # or parse HTML
                        
                        # Validate data
                        validation = self.data_validator.validate_price_data(
                            symbol, data.get('price'), data.get('volume')
                        )
                        
                        if validation['is_valid']:
                            self.monitor.record_request(source, True, time.time() - start_time)
                            return data
                        else:
                            logger.warning(f"Invalid data from {source}: {validation['issues']}")
                            
                    else:
                        error_type = self.error_classifier.classify_error(None, response.status)
                        self.monitor.record_request(source, False, time.time() - start_time, error_type)
                        
                        if error_type == 'rate_limit':
                            self.rate_limiter.record_rate_limit_hit(source)
                            
        except Exception as e:
            error_type = self.error_classifier.classify_error(e)
            self.monitor.record_request(source, False, time.time() - start_time, error_type)
            
        return None
