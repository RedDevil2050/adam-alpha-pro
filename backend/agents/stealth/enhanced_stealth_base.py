"""
Enhanced Stealth Agent Base Class - Fixed Version
================================================

Upgraded base class with adaptive rate limiting, circuit breakers,
and intelligent error handling for improved reliability.
"""

import asyncio
import time
import aiohttp
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from backend.agents.stealth.advanced_base import AdvancedStealthAgentBase, QuadChannelData
from backend.agents.stealth.safe_data_utils import (
    safe_get_price, safe_get_volume, validate_indian_market_data,
    log_data_extraction_result
)
from loguru import logger


@dataclass
class RateLimitTracker:
    """Track rate limits and adapt requests dynamically"""
    requests_per_minute: int = 60
    current_requests: int = 0
    reset_time: float = 0
    backoff_multiplier: float = 1.0
    consecutive_failures: int = 0
    last_success_time: float = 0


@dataclass 
class CircuitBreakerState:
    """Circuit breaker state for handling failing sources"""
    failure_count: int = 0
    last_failure_time: float = 0
    state: str = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    failure_threshold: int = 3
    recovery_timeout: float = 300  # 5 minutes


class EnhancedStealthAgentBase(AdvancedStealthAgentBase):
    """Enhanced stealth agent with adaptive rate limiting and circuit breakers"""
    
    def __init__(self):
        super().__init__()
        self.rate_limiters = {}
        # Don't override circuit_breakers - use the ones from parent class
        # self.circuit_breakers = {}  # This was overriding parent's circuit breakers!
        self.url_patterns = self._get_url_patterns()
        # Keep the parent's performance_metrics structure and add enhanced metrics
        self.enhanced_performance_metrics = {}
        
    def _get_url_patterns(self) -> Dict[str, List[str]]:
        """Override in subclasses to provide URL patterns for fallback"""
        return {}
    
    async def _adaptive_rate_limit(self, source: str) -> None:
        """Apply adaptive rate limiting based on source performance"""
        if source not in self.rate_limiters:
            self.rate_limiters[source] = RateLimitTracker()
            
        tracker = self.rate_limiters[source]
        
        # Reset counter if a minute has passed
        if time.time() > tracker.reset_time:
            tracker.current_requests = 0
            tracker.reset_time = time.time() + 60
            
        # Check if we need to wait
        if tracker.current_requests >= tracker.requests_per_minute:
            wait_time = tracker.reset_time - time.time()
            if wait_time > 0:
                logger.info(f"⏳ Rate limit reached for {source}, waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time * tracker.backoff_multiplier)
                
        tracker.current_requests += 1
    
    def _record_rate_limit_hit(self, source: str) -> None:
        """Record when we hit a rate limit to adapt future requests"""
        if source in self.rate_limiters:
            tracker = self.rate_limiters[source]
            tracker.requests_per_minute = max(10, int(tracker.requests_per_minute * 0.7))
            tracker.backoff_multiplier = min(3.0, tracker.backoff_multiplier * 1.5)
            tracker.consecutive_failures += 1
            logger.warning(f"🐌 Reduced rate limit for {source} to {tracker.requests_per_minute}/min")

    def _check_circuit_breaker(self, source: str) -> bool:
        """Check if circuit breaker allows requests to this source"""
        # Use parent's circuit breaker system instead of our own
        if hasattr(self, 'circuit_breakers') and source in self.circuit_breakers:
            return self.circuit_breakers[source].can_execute()
        return True

    def _record_success(self, source: str) -> None:
        """Record successful request"""
        if source in self.rate_limiters:
            self.rate_limiters[source].consecutive_failures = 0
            self.rate_limiters[source].last_success_time = time.time()
            
        # Use parent's circuit breaker record_success method
        if hasattr(self, 'circuit_breakers') and source in self.circuit_breakers:
            self.circuit_breakers[source].record_success()

    def _record_failure(self, source: str, error: Exception) -> None:
        """Record failed request and update circuit breaker"""
        # Use parent's circuit breaker record_failure method
        if hasattr(self, 'circuit_breakers') and source in self.circuit_breakers:
            self.circuit_breakers[source].record_failure()
        
        # Handle specific error types
        error_str = str(error).lower()
        if "429" in error_str or "rate limit" in error_str:
            self._record_rate_limit_hit(source)
    async def _find_working_url(self, source: str, symbol: str, session: aiohttp.ClientSession) -> Optional[str]:
        """Find the first working URL for a source and symbol"""
        if source not in self.url_patterns:
            return None
            
        symbol_variants = {
            'symbol': symbol,
            'symbol_lower': symbol.lower()
        }
        for url_pattern in self.url_patterns[source]:
            try:
                url = url_pattern.format(**symbol_variants)
                response = await session.head(url, timeout=aiohttp.ClientTimeout(total=5))
                if response.status in [200, 301, 302]:
                    logger.debug(f"✅ Found working URL for {source}: {url}")
                    return url
            except Exception as e:
                logger.debug(f"❌ URL failed for {source}: {url} - {e}")
                continue
                
        logger.warning(f"⚠️ No working URL found for {source}:{symbol}")
        return None
    
    async def _enhanced_fetch_with_fallback(self, source: str, symbol: str, 
                                           fetch_func, *args, **kwargs) -> Optional[Dict]:
        """Enhanced fetch with circuit breaker, rate limiting, and URL fallback"""
        
        # Check circuit breaker
        if not self._check_circuit_breaker(source):
            logger.warning(f"🔴 Circuit breaker OPEN for {source}, skipping")
            return None
        
        # Apply rate limiting
        await self._adaptive_rate_limit(source)
        
        try:
            start_time = time.time()
            result = await fetch_func(*args, **kwargs)
            
            if result:
                response_time = time.time() - start_time
                self._record_performance(source, True, response_time)
                self._record_success(source)
                
                # Extract and validate data
                price = safe_get_price(result, symbol)
                volume = safe_get_volume(result, symbol)
                validation = validate_indian_market_data(price, volume, symbol)
                
                log_data_extraction_result(source, symbol, price, volume, validation['is_valid'])
                
                # Add validation score to result
                result['validation_score'] = validation['confidence']
                result['validation_issues'] = validation['issues']
                
                return result
            else:
                self._record_performance(source, False, time.time() - start_time)
                return None
                
        except Exception as e:
            self._record_failure(source, e)
            self._record_performance(source, False, time.time() - start_time)
            logger.warning(f"❌ {source} fetch failed for {symbol}: {e}")
            return None

    def _record_performance(self, source: str, success: bool, response_time: float) -> None:
        """Record performance metrics for optimization"""
        if source not in self.enhanced_performance_metrics:
            self.enhanced_performance_metrics[source] = {
                'success_count': 0,
                'failure_count': 0,
                'avg_response_time': 0.0,
                'total_requests': 0
            }
        
        metrics = self.enhanced_performance_metrics[source]
        metrics['total_requests'] += 1
        
        if success:
            metrics['success_count'] += 1
        else:
            metrics['failure_count'] += 1
            
        # Update average response time safely
        total_requests = metrics['total_requests']
        if total_requests > 0:
            metrics['avg_response_time'] = (
                (metrics['avg_response_time'] * (total_requests - 1) + response_time) 
                / total_requests
            )

    def get_optimized_channel_priority(self) -> List[str]:
        """Get optimized channel priority based on performance"""
        channels = ['primary', 'secondary', 'tertiary', 'emergency']
        
        def channel_score(channel):
            if channel not in self.enhanced_performance_metrics:
                return 0.5  # Default score for unknown channels
                
            metrics = self.enhanced_performance_metrics[channel]
            total_requests = metrics.get('total_requests', 0)
            if total_requests == 0:
                return 0.5
                
            success_count = metrics.get('success_count', 0)
            avg_response_time = metrics.get('avg_response_time', 30)
            
            success_rate = success_count / total_requests
            response_score = max(0, 1 - (avg_response_time / 30))  # Normalize to 30s max
            
            return (success_rate * 0.7) + (response_score * 0.3)
        
        return sorted(channels, key=channel_score, reverse=True)

    def get_health_report(self) -> Dict[str, Any]:
        """Get health report for all sources"""
        report = {
            'timestamp': time.time(),
            'sources': {},
            'overall_health': 'HEALTHY'
        }
        
        unhealthy_count = 0
        
        for source in self.enhanced_performance_metrics:
            metrics = self.enhanced_performance_metrics[source]
            total_requests = metrics.get('total_requests', 0)
            success_count = metrics.get('success_count', 0)
            
            success_rate = success_count / max(total_requests, 1)
            
            # Get circuit breaker state from parent's circuit breaker system
            circuit_state = "UNKNOWN"
            if hasattr(self, 'circuit_breakers') and source in self.circuit_breakers:
                # Access the parent's CircuitBreaker state
                circuit_breaker = self.circuit_breakers[source]
                if hasattr(circuit_breaker, 'state'):
                    circuit_state = circuit_breaker.state
                elif hasattr(circuit_breaker, 'can_execute'):
                    # If no state attribute, infer from can_execute
                    circuit_state = "CLOSED" if circuit_breaker.can_execute() else "OPEN"
            
            source_health = "HEALTHY"
            if success_rate < 0.5 or circuit_state == "OPEN":
                source_health = "UNHEALTHY"
                unhealthy_count += 1
            elif success_rate < 0.8 or circuit_state == "HALF_OPEN":
                source_health = "DEGRADED"
            
            avg_response_time = metrics.get('avg_response_time', 0)
            
            report['sources'][source] = {
                'health': source_health,
                'success_rate': round(success_rate * 100, 1),
                'avg_response_time': round(avg_response_time, 2),
                'total_requests': total_requests,
                'circuit_breaker': circuit_state
            }
        
        # Overall health assessment
        total_sources = len(self.enhanced_performance_metrics)
        if total_sources > 0:
            unhealthy_ratio = unhealthy_count / total_sources
            if unhealthy_ratio > 0.5:
                report['overall_health'] = 'CRITICAL'
            elif unhealthy_ratio > 0.25:
                report['overall_health'] = 'DEGRADED'
        
        return report
