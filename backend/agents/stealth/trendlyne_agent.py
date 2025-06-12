from backend.agents.stealth.advanced_base import AdvancedStealthAgentBase, QuadChannelData
from backend.agents.stealth.safe_data_utils import (
    safe_numeric_compare, safe_get_price, safe_get_volume, safe_get_float,
    validate_indian_market_data
)
from backend.utils.symbol_normalizer_fixed import IndianEquitySymbolNormalizer
import httpx
from typing import Dict, List, Optional, Any
from loguru import logger
from bs4 import BeautifulSoup
import time
import random
import asyncio

agent_name = "trendlyne_agent"


class TrendlyneAgent(AdvancedStealthAgentBase):
    """Enhanced TrendLyne Agent with improved circuit breaker and retry logic"""
    
    def __init__(self):
        super().__init__()
        # TrendLyne-specific symbol to URL mapping
        self.trendlyne_symbol_map = {
            'RELIANCE': 'reliance-industries-500325',
            'TCS': 'tata-consultancy-services-532540',
            'INFY': 'infosys-500209',
            'HDFC': 'hdfc-bank-500180',
            'HDFCBANK': 'hdfc-bank-500180',
            'ICICIBANK': 'icici-bank-532174',
            'SBIN': 'state-bank-of-india-500112',
            'ITC': 'itc-500875',
            'WIPRO': 'wipro-507685',
            'MARUTI': 'maruti-suzuki-india-532500',
            'BHARTIARTL': 'bharti-airtel-532454',
            'HCLTECH': 'hcl-technologies-532281',
            'AXISBANK': 'axis-bank-532215',
            'LT': 'larsen-toubro-500510',
            'ASIANPAINT': 'asian-paints-500820',
            'NESTLEIND': 'nestle-india-500790',
            'ULTRACEMCO': 'ultratech-cement-532538',
            'KOTAKBANK': 'kotak-mahindra-bank-500247',
            'BAJFINANCE': 'bajaj-finance-500034',
            'TITAN': 'titan-company-500114'
        }
        
        # Circuit breaker settings for different channels
        self.circuit_breaker_config = {
            'primary': {'max_failures': 3, 'timeout': 60, 'current_failures': 0, 'last_failure': 0},
            'secondary': {'max_failures': 5, 'timeout': 45, 'current_failures': 0, 'last_failure': 0},
            'tertiary': {'max_failures': 4, 'timeout': 30, 'current_failures': 0, 'last_failure': 0},
            'emergency': {'max_failures': 2, 'timeout': 120, 'current_failures': 0, 'last_failure': 0}
        }
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 2.0  # Minimum 2 seconds between requests
        
        logger.info("🚀 Enhanced TrendLyne Agent initialized with improved circuit breaker")
    
    async def _apply_rate_limiting(self):
        """Apply rate limiting between requests"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
            await asyncio.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _is_circuit_breaker_open(self, channel: str) -> bool:
        """Check if circuit breaker is open for a channel"""
        config = self.circuit_breaker_config.get(channel, {})
        current_time = time.time()
        
        if config.get('current_failures', 0) >= config.get('max_failures', 3):
            if current_time - config.get('last_failure', 0) < config.get('timeout', 60):
                logger.warning(f"🔴 Circuit breaker OPEN for {channel} channel")
                return True
            else:
                # Reset circuit breaker after timeout
                config['current_failures'] = 0
                logger.info(f"🟡 Circuit breaker RESET for {channel} channel")
                return False
        
        return False
    
    def _record_failure(self, channel: str):
        """Record a failure for circuit breaker"""
        config = self.circuit_breaker_config.get(channel, {})
        config['current_failures'] = config.get('current_failures', 0) + 1
        config['last_failure'] = time.time()
        logger.debug(f"📊 {channel} channel failures: {config['current_failures']}/{config.get('max_failures', 3)}")
    
    def _record_success(self, channel: str):
        """Record a success for circuit breaker"""
        config = self.circuit_breaker_config.get(channel, {})
        config['current_failures'] = 0
        logger.debug(f"✅ {channel} channel success - failures reset")
    
    async def _fetch_with_exponential_backoff(self, fetch_func, symbol: str, channel: str, max_retries: int = 3):
        """Fetch data with exponential backoff retry logic"""
        if self._is_circuit_breaker_open(channel):
            logger.warning(f"⚠️ Skipping {channel} fetch for {symbol} - circuit breaker open")
            return None
        
        for attempt in range(max_retries):
            try:
                # Apply rate limiting
                await self._apply_rate_limiting()
                
                # Calculate backoff delay
                if attempt > 0:
                    backoff_delay = (2 ** attempt) + random.uniform(0, 1)
                    logger.debug(f"🔄 Retry {attempt + 1}/{max_retries} for {channel} after {backoff_delay:.2f}s")
                    await asyncio.sleep(backoff_delay)
                
                # Attempt the fetch
                result = await fetch_func(symbol)
                
                if result:
                    self._record_success(channel)
                    logger.success(f"✅ {channel} fetch successful for {symbol} on attempt {attempt + 1}")
                    return result
                else:
                    logger.debug(f"📭 {channel} fetch returned no data for {symbol} on attempt {attempt + 1}")
                    
            except Exception as e:
                logger.warning(f"❌ {channel} fetch attempt {attempt + 1} failed for {symbol}: {e}")
                if attempt == max_retries - 1:
                    self._record_failure(channel)
        
        logger.error(f"💥 {channel} fetch exhausted all {max_retries} retries for {symbol}")
        self._record_failure(channel)
        return None

    # REQUIRED ABSTRACT METHOD IMPLEMENTATIONS
    async def _fetch_primary_source(self, symbol: str) -> Optional[Dict]:
        """Fetch data from TrendLyne primary source with circuit breaker"""
        return await self._fetch_with_exponential_backoff(
            self._fetch_trendlyne_data, symbol, 'primary', max_retries=3
        )
    
    async def _fetch_secondary_source(self, symbol: str) -> Optional[Dict]:
        """Fetch data from TrendLyne secondary source with circuit breaker"""
        return await self._fetch_with_exponential_backoff(
            self._fetch_trendlyne_data, symbol, 'secondary', max_retries=4
        )
    
    async def _fetch_tertiary_source(self, symbol: str) -> Optional[Dict]:
        """Fetch data from TrendLyne tertiary source with circuit breaker"""
        parent_method = super()._fetch_tertiary_source
        
        async def tertiary_fetch(sym):
            return await parent_method(sym)
        
        return await self._fetch_with_exponential_backoff(
            tertiary_fetch, symbol, 'tertiary', max_retries=3
        )
    
    async def _fetch_emergency_source(self, symbol: str) -> Optional[Dict]:
        """Fetch data from emergency source with circuit breaker"""
        parent_method = super()._fetch_emergency_source
        
        async def emergency_fetch(sym):
            return await parent_method(sym)
        
        return await self._fetch_with_exponential_backoff(
            emergency_fetch, symbol, 'emergency', max_retries=2
        )
    
    async def _find_working_url(self, source: str, symbol: str, session) -> Optional[str]:
        """Override to use TrendLyne-specific URL generation with improved redirect handling"""
        if source != 'trendlyne':
            return await super()._find_working_url(source, symbol, session)
        
        urls = self._get_trendlyne_urls(symbol)
        
        for url in urls:
            try:
                # Use GET instead of HEAD for better compatibility with redirects
                response = await session.get(url, timeout=8, follow_redirects=False)
                
                if response.status_code == 200:
                    logger.debug(f"✅ Found working TrendLyne URL: {url}")
                    return url
                elif response.status_code in [301, 302, 303, 307, 308]:
                    # Handle redirects manually for better control
                    redirect_url = response.headers.get('location')
                    if redirect_url:
                        # Make redirect URL absolute if it's relative
                        if redirect_url.startswith('/'):
                            from urllib.parse import urljoin
                            redirect_url = urljoin(url, redirect_url)
                        
                        # Test the redirect URL
                        try:
                            redirect_response = await session.get(redirect_url, timeout=8, follow_redirects=False)
                            if redirect_response.status_code == 200:
                                logger.debug(f"✅ Found working TrendLyne URL after redirect: {redirect_url}")
                                return redirect_url
                        except Exception as redirect_error:
                            logger.debug(f"❌ Redirect URL failed: {redirect_url} - {redirect_error}")
                            continue
                    
                logger.debug(f"❌ TrendLyne URL returned {response.status_code}: {url}")
                    
            except Exception as e:
                logger.debug(f"❌ TrendLyne URL failed: {url} - {e}")
                continue
        
        logger.warning(f"⚠️ No working TrendLyne URL found for {symbol}")
        return None

    async def _fetch_trendlyne_data(self, symbol: str) -> Optional[Dict]:
        """Fetch data from TrendLyne with enhanced error handling and redirect support"""
        headers = {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Referer': 'https://www.google.com/',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'DNT': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none'
        }
        
        # Enhanced client configuration with connection pooling
        limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
        timeout = httpx.Timeout(12.0, connect=6.0, read=12.0, write=6.0)
        
        try:
            async with httpx.AsyncClient(
                headers=headers, 
                timeout=timeout,
                limits=limits,
                follow_redirects=False,  # Handle redirects manually
                http2=False  # Disable HTTP/2 for better compatibility
            ) as session:
                # First try to find a working URL
                working_url = await self._find_working_url('trendlyne', symbol, session)
                
                if not working_url:
                    logger.warning(f"TrendLyne: No working URL found for {symbol}")
                    return None
                
                # Add random jitter before request
                await asyncio.sleep(random.uniform(0.3, 1.0))
                
                # Fetch with manual redirect handling
                response = await self._fetch_with_redirect_handling(session, working_url, max_redirects=3)
                
                if not response:
                    logger.warning(f"TrendLyne: Failed to fetch data after redirect handling for {symbol}")
                    return None
                
                if response.status_code == 200:
                    html_content = response.text
                    
                    # Validate content length
                    if len(html_content) < 1000:
                        logger.warning(f"TrendLyne: Suspiciously short content for {symbol} ({len(html_content)} chars)")
                        return None
                    
                    # Extract data from HTML
                    data = self._parse_trendlyne_html(html_content, symbol)
                    
                    if data:
                        logger.success(f"TrendLyne: Successfully fetched data for {symbol}")
                        return data
                    else:
                        logger.warning(f"TrendLyne: Could not parse data for {symbol}")
                        return None
                else:
                    logger.warning(f"TrendLyne: HTTP {response.status_code} for {symbol}")
                    return None
                    
        except httpx.TimeoutException:
            logger.warning(f"TrendLyne: Timeout for {symbol}")
            return None
        except httpx.ConnectError:
            logger.warning(f"TrendLyne: Connection error for {symbol}")
            return None
        except httpx.HTTPStatusError as e:
            logger.warning(f"TrendLyne: HTTP status error for {symbol}: {e}")
            return None
        except Exception as e:
            logger.error(f"TrendLyne: Unexpected error fetching {symbol}: {e}")
            return None

    async def _fetch_with_redirect_handling(self, session, url: str, max_redirects: int = 3) -> Optional[httpx.Response]:
        """Fetch URL with manual redirect handling for better control"""
        current_url = url
        redirect_count = 0
        
        while redirect_count < max_redirects:
            try:
                response = await session.get(current_url, follow_redirects=False)
                
                if response.status_code == 200:
                    return response
                elif response.status_code in [301, 302, 303, 307, 308]:
                    redirect_url = response.headers.get('location')
                    if not redirect_url:
                        logger.warning(f"TrendLyne: Redirect without location header from {current_url}")
                        return None
                    
                    # Make redirect URL absolute if it's relative
                    if redirect_url.startswith('/'):
                        from urllib.parse import urljoin
                        redirect_url = urljoin(current_url, redirect_url)
                    
                    logger.debug(f"TrendLyne: Following redirect {redirect_count + 1}/{max_redirects}: {current_url} -> {redirect_url}")
                    current_url = redirect_url
                    redirect_count += 1
                    
                    # Add small delay between redirects
                    await asyncio.sleep(random.uniform(0.2, 0.5))
                    
                elif response.status_code == 404:
                    logger.warning(f"TrendLyne: Symbol not found (404) at {current_url}")
                    return None
                elif response.status_code == 403:
                    logger.warning(f"TrendLyne: Access forbidden (403) at {current_url} - may be rate limited")
                    return None
                elif response.status_code == 429:
                    logger.warning(f"TrendLyne: Rate limited (429) at {current_url}")
                    return None
                elif response.status_code >= 500:
                    logger.warning(f"TrendLyne: Server error {response.status_code} at {current_url}")
                    return None
                else:
                    logger.warning(f"TrendLyne: Unhandled status {response.status_code} at {current_url}")
                    return None
                    
            except Exception as e:
                logger.warning(f"TrendLyne: Error during redirect handling at {current_url}: {e}")
                return None
        
        logger.warning(f"TrendLyne: Too many redirects (>{max_redirects}) starting from {url}")
        return None

    def _parse_trendlyne_html(self, html_content: str, symbol: str) -> Optional[Dict]:
        """Parse TrendLyne HTML to extract stock data"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for price data in various possible locations
            price = None
            volume = None
            
            # Method 1: Look for price in specific class names (TrendLyne specific)
            price_selectors = [
                '.current-price',
                '.stock-price', 
                '.price-current',
                '[data-field="price"]',
                '.quote-price',
                '.last-price',
                '.ltp',
                '.price-ltp',
                '.stock-ltp'
            ]
            
            for selector in price_selectors:
                price_element = soup.select_one(selector)
                if price_element:
                    price_text = price_element.get_text(strip=True)
                    price = self._extract_number(price_text)
                    if price and 10 <= price <= 100000:  # Reasonable range for Indian stocks
                        break
            
            # Method 2: Look for volume data
            volume_selectors = [
                '.volume',
                '[data-field="volume"]',
                '.trade-volume',
                '.vol',
                '.volume-traded'
            ]
            
            for selector in volume_selectors:
                volume_element = soup.select_one(selector)
                if volume_element:
                    volume_text = volume_element.get_text(strip=True)
                    volume = self._extract_volume_number(volume_text)
                    if volume:
                        break
            
            # Method 3: Look in script tags for JSON data
            if not price:
                script_tags = soup.find_all('script')
                for script in script_tags:
                    if script.string and ('price' in script.string.lower() or 'quote' in script.string.lower()):
                        # Try to extract price from script content
                        import re
                        price_match = re.search(r'"price"[:\s]*([0-9.]+)', script.string)
                        if price_match:
                            price = float(price_match.group(1))
                            if 10 <= price <= 100000:
                                break
            
            # Method 4: Look for meta tags with price data
            if not price:
                meta_tags = soup.find_all('meta')
                for meta in meta_tags:
                    content = meta.get('content', '')
                    if 'price' in meta.get('property', '').lower() or 'price' in meta.get('name', '').lower():
                        price = self._extract_number(content)
                        if price and 10 <= price <= 100000:
                            break
            
            if price and price > 0:
                return {
                    'symbol': symbol,
                    'price': price,
                    'volume': volume or 0,
                    'source': 'trendlyne',
                    'timestamp': time.time(),
                    'data_quality': 'high' if volume else 'medium'
                }
            else:
                logger.warning(f"TrendLyne: Could not extract valid price for {symbol}")
                return None
                
        except Exception as e:
            logger.error(f"TrendLyne: Error parsing HTML for {symbol}: {e}")
            return None
    
    def _extract_number(self, text: str) -> Optional[float]:
        """Extract number from text, handling Indian number format"""
        if not text:
            return None
        
        try:
            import re
            # Remove common text and symbols, but keep numbers and decimal points
            cleaned = re.sub(r'[^\d.,]', '', text.replace('₹', '').replace('Rs', ''))
            cleaned = cleaned.replace(',', '')
            
            if cleaned and '.' in cleaned:
                # Handle decimal numbers
                return float(cleaned)
            elif cleaned:
                # Handle integer numbers
                return float(cleaned)
        except (ValueError, TypeError):
            pass
        
        return None
    
    def _extract_volume_number(self, text: str) -> Optional[int]:
        """Extract volume number from text, handling Indian format (crores, lakhs)"""
        if not text:
            return None
        
        try:
            import re
            text_lower = text.lower()
            
            # Extract number part
            number_match = re.search(r'([\d.,]+)', text_lower)
            if not number_match:
                return None
            
            number_str = number_match.group(1).replace(',', '')
            base_number = float(number_str)
            
            # Handle Indian volume units
            if 'crore' in text_lower or 'cr' in text_lower:
                return int(base_number * 10000000)  # 1 crore = 10 million
            elif 'lakh' in text_lower or 'lac' in text_lower:
                return int(base_number * 100000)    # 1 lakh = 100 thousand
            elif 'k' in text_lower:
                return int(base_number * 1000)      # 1k = 1000
            else:
                return int(base_number)
                
        except (ValueError, TypeError):
            pass
        
        return None
    
    def _extract_best_data(self, fused_data: QuadChannelData) -> Dict:
        """Extract the best available data from quad-channel fusion."""
        # Priority order: primary -> secondary -> tertiary -> emergency
        for channel in ["primary", "secondary", "tertiary", "emergency"]:
            channel_data = getattr(fused_data, channel)
            if channel_data:
                # Check for price data in various formats
                price = None
                for price_key in ["price", "close", "last", "current_price", "ltp"]:
                    if price_key in channel_data and channel_data[price_key]:
                        try:
                            price = float(str(channel_data[price_key]).replace(',', '').replace('₹', '').replace('$', ''))
                            if 10 <= price <= 100000:  # Reasonable range for Indian stocks
                                break
                        except (ValueError, TypeError):
                            continue
                
                if price:
                    volume = safe_get_volume(channel_data)
                    symbol_name = channel_data.get('symbol', '')
                    validation_result = validate_indian_market_data(price, volume, symbol_name)
                    return {
                        'price': price,
                        'volume': volume,
                        'source': channel_data.get('source', f'trendlyne_{channel}'),
                        'timestamp': channel_data.get('timestamp', time.time()),
                        'validation_score': validation_result.get('confidence', 0.5) if isinstance(validation_result, dict) else 0.5
                    }
        
        return {}
    
    async def _execute_analysis(self, symbol: str, agent_outputs: dict, fused_data: QuadChannelData) -> Dict[str, Any]:
        """Execute TrendLyne-specific analysis"""
        logger.info(f"🔬 Starting enhanced TrendLyne analysis for {symbol}")
        
        # Extract the best available data
        data = self._extract_best_data(fused_data)
        
        if not data:
            logger.warning(f"TrendLyne: No valid data available for analysis of {symbol}")
            return {
                'signal': 'NO_DATA',
                'confidence': 0.0,
                'score': 0.0,
                'factors': {'error': 'No data available'},
                'validation_score': 0.0
            }
        
        # Calculate base score
        base_score = self._calculate_base_score(data, symbol)
        
        # Apply enhancements
        enhanced_score = self._calculate_enhanced_score(base_score, fused_data)
        enhanced_confidence = self._calculate_enhanced_confidence(base_score, fused_data)
        
        # Determine signal
        signal = self._determine_signal(enhanced_score)
        
        return {
            'signal': signal,
            'confidence': enhanced_confidence,
            'score': enhanced_score,
            'factors': self._get_analysis_factors(data, fused_data),
            'validation_score': data.get('validation_score', 0.5)
        }
    
    def _calculate_base_score(self, data: Dict, symbol: str) -> float:
        """Calculate base score for TrendLyne analysis"""
        try:
            price = data.get('price', 0)
            volume = data.get('volume', 0)
            
            # Basic scoring logic
            if price <= 0:
                return 0.0
            
            # Price-based scoring (relative to typical Indian stock ranges)
            price_score = 0.5
            if 100 <= price <= 3000:  # Sweet spot for many Indian stocks
                price_score = 0.7
            elif price > 3000:
                price_score = 0.6  # High-priced stocks
            
            # Volume-based scoring
            volume_score = 0.3
            if volume > 100000:
                volume_score = 0.5
            if volume > 1000000:
                volume_score = 0.7
            
            # Combine scores
            base_score = (price_score * 0.7) + (volume_score * 0.3)
            
            return min(max(base_score, 0.0), 1.0)
            
        except Exception as e:
            logger.warning(f"TrendLyne: Error calculating base score for {symbol}: {e}")
            return 0.5

    def _calculate_enhanced_score(self, base_score: float, fused_data: QuadChannelData) -> float:
        """Calculate enhanced score using quad-channel data"""
        try:
            # Start with base score
            enhanced_score = base_score
            
            # Boost based on number of channels with data
            channel_boost = len(fused_data.channels_used) * 0.05  # 5% per channel
            enhanced_score += channel_boost
            
            # Boost based on fusion confidence
            fusion_boost = fused_data.fusion_confidence * 0.1
            enhanced_score += fusion_boost
            
            # Boost based on validation score
            validation_boost = fused_data.validation_score * 0.05
            enhanced_score += validation_boost
            
            return min(max(enhanced_score, 0.0), 1.0)
            
        except Exception as e:
            logger.warning(f"TrendLyne: Error calculating enhanced score: {e}")
            return base_score

    def _calculate_enhanced_confidence(self, base_score: float, fused_data: QuadChannelData) -> float:
        """Calculate enhanced confidence with quad-channel boost"""
        try:
            # Base confidence from score
            base_confidence = base_score * 0.8
            
            # Boost from multiple channels
            channel_boost = len(fused_data.channels_used) * 0.04  # 4% per channel
            
            # Boost from fusion confidence
            fusion_boost = fused_data.fusion_confidence * 0.1
            
            # Boost from validation
            validation_boost = fused_data.validation_score * 0.06
            
            total_confidence = base_confidence + channel_boost + fusion_boost + validation_boost
            
            return min(max(total_confidence, 0.0), 1.0)
            
        except Exception as e:
            logger.warning(f"TrendLyne: Error calculating confidence: {e}")
            return base_score * 0.8

    def _determine_signal(self, score: float) -> str:
        """Determine trading signal based on score"""
        if score >= 0.8:
            return "STRONG_BUY"
        elif score >= 0.65:
            return "BUY"
        elif score >= 0.45:
            return "HOLD"
        elif score >= 0.3:
            return "WEAK_HOLD"
        else:
            return "SELL"

    def _get_analysis_factors(self, data: Dict, fused_data: QuadChannelData) -> Dict:
        """Get analysis factors for detailed breakdown"""
        try:
            return {
                "price_data": {
                    "current_price": data.get('price', 0),
                    "volume": data.get('volume', 0),
                    "source": data.get('source', 'unknown')
                },
                "data_quality": {
                    "channels_used": fused_data.channels_used,
                    "fusion_confidence": fused_data.fusion_confidence,
                    "validation_score": fused_data.validation_score,
                    "collection_timestamp": fused_data.collection_timestamp
                },
                "trendlyne_metrics": {
                    "price_range_assessment": self._assess_price_range(data.get('price', 0)),
                    "volume_strength": self._assess_volume_strength(data.get('volume', 0)),
                    "data_availability": "good" if data else "poor"
                }
            }
        except Exception as e:
            logger.warning(f"TrendLyne: Error generating analysis factors: {e}")
            return {"error": str(e)}

    def _assess_price_range(self, price: float) -> str:
        """Assess price range for Indian stocks"""
        if price <= 0:
            return "invalid"
        elif price < 50:
            return "penny_stock"
        elif price < 500:
            return "low_priced"
        elif price < 3000:
            return "mid_priced"
        else:
            return "high_priced"

    def _assess_volume_strength(self, volume: int) -> str:
        """Assess volume strength"""
        if volume <= 0:
            return "no_volume"
        elif volume < 10000:
            return "low"
        elif volume < 100000:
            return "moderate"
        elif volume < 1000000:
                        return "high"
        else:
            return "very_high"
    
    def _get_url_patterns(self) -> Dict[str, List[str]]:
        """Get TrendLyne URL patterns - will be dynamically generated"""
        return {
            'trendlyne': []  # Will be populated by _get_trendlyne_urls
        }
    
    def _get_trendlyne_urls(self, symbol: str) -> List[str]:
        """Generate TrendLyne URLs for a given symbol"""
        urls = []
        
        # Check if we have a direct mapping
        if symbol in self.trendlyne_symbol_map:
            company_slug = self.trendlyne_symbol_map[symbol]
            urls.extend([
                f"https://www.trendlyne.com/equity/{company_slug}/",
                f"https://trendlyne.com/equity/{company_slug}/",
                f"https://www.trendlyne.com/equity/{company_slug}",
                f"https://trendlyne.com/equity/{company_slug}"
            ])
        
        # Fallback patterns (these will likely fail but worth trying)
        symbol_lower = symbol.lower()
        urls.extend([
            f"https://www.trendlyne.com/equity/{symbol}/",
            f"https://trendlyne.com/equity/{symbol}/",
            f"https://www.trendlyne.com/equity/{symbol_lower}/",
            f"https://trendlyne.com/equity/{symbol_lower}/",
            f"https://www.trendlyne.com/stocks/{symbol}/",
            f"https://trendlyne.com/stocks/{symbol}/",
            f"https://www.trendlyne.com/stocks/{symbol_lower}/",
            f"https://trendlyne.com/stocks/{symbol_lower}/"
        ])
        
        return urls

    def _normalize_symbol_for_yahoo(self, symbol: str) -> str:
        """Normalize Indian equity symbol for Yahoo Finance API."""
        normalizer = IndianEquitySymbolNormalizer()
        return normalizer.normalize_for_yahoo(symbol)

    def _enhance_with_quad_metadata(self, result: dict, fused_data: QuadChannelData) -> dict:
        """Enhance result with quad-channel metadata."""
        if not isinstance(result, dict):
            return result
            
        result["quad_channel_metadata"] = {
            "channels_used": fused_data.channels_used,
            "fusion_confidence": fused_data.fusion_confidence,
            "validation_score": fused_data.validation_score,
            "collection_timestamp": fused_data.collection_timestamp,
            "data_quality_metrics": {
                "total_channels": len(fused_data.channels_used),
                "successful_channels": len([c for c in fused_data.channels_used if getattr(fused_data, c)]),
                "fusion_method": "weighted_average"
            }
        }
        return result

async def run(symbol: str, agent_outputs: dict = {}) -> dict:
    """Run TrendLyne agent analysis"""
    agent = TrendlyneAgent()
    return await agent.execute(symbol, agent_outputs=agent_outputs)
