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
        # TrendLyne-specific symbol to URL mapping - Updated with WORKING 2024 patterns
        self.trendlyne_symbol_map = {
            'RELIANCE': 'reliance-industries-limited-ril',
            'TCS': 'tata-consultancy-services-tcs', 
            'INFY': 'infosys-limited-infy',
            'HDFC': 'hdfc-bank-limited-hdfcbank',
            'HDFCBANK': 'hdfc-bank-limited-hdfcbank',
            'ICICIBANK': 'icici-bank-limited-icicibank',
            'SBIN': 'state-bank-of-india-sbin',
            'ITC': 'itc-limited-itc',
            'WIPRO': 'wipro-limited-wipro',
            'MARUTI': 'maruti-suzuki-india-limited-maruti',
            'BHARTIARTL': 'bharti-airtel-limited-bhartiartl',
            'HCLTECH': 'hcl-technologies-limited-hcltech',
            'AXISBANK': 'axis-bank-limited-axisbank',
            'LT': 'larsen-toubro-limited-lt',
            'ASIANPAINT': 'asian-paints-limited-asianpaint',
            'NESTLEIND': 'nestle-india-limited-nestleind',
            'ULTRACEMCO': 'ultratech-cement-limited-ultracemco',
            'KOTAKBANK': 'kotak-mahindra-bank-limited-kotakbank',
            'BAJFINANCE': 'bajaj-finance-limited-bajfinance',
            'TITAN': 'titan-company-limited-titan'
        }
        
        # Circuit breaker settings - More lenient for live scraping
        self.circuit_breaker_config = {
            'primary': {'max_failures': 5, 'timeout': 30, 'current_failures': 0, 'last_failure': 0},
            'secondary': {'max_failures': 4, 'timeout': 25, 'current_failures': 0, 'last_failure': 0},
            'tertiary': {'max_failures': 3, 'timeout': 20, 'current_failures': 0, 'last_failure': 0},
            'emergency': {'max_failures': 2, 'timeout': 40, 'current_failures': 0, 'last_failure': 0}
        }
        
        # Rate limiting - Balanced for live data without being blocked
        self.last_request_time = 0
        self.min_request_interval = 0.8  # Slightly faster but still respectful
        
        logger.info("🚀 Enhanced TrendLyne Agent initialized for live data scraping")
    
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
        logger.debug(f"🎯 TrendLyne primary source fetch starting for {symbol}")
        result = await self._fetch_with_exponential_backoff(
            self._fetch_trendlyne_data, symbol, 'primary', max_retries=3
        )
        if result:
            logger.success(f"✅ TrendLyne primary source successful for {symbol}: price={result.get('price')}")
        else:
            logger.warning(f"❌ TrendLyne primary source failed for {symbol}")
        return result
    
    async def _fetch_secondary_source(self, symbol: str) -> Optional[Dict]:
        """Fetch data from TrendLyne secondary source with circuit breaker"""
        logger.debug(f"🎯 TrendLyne secondary source fetch starting for {symbol}")
        result = await self._fetch_with_exponential_backoff(
            self._fetch_trendlyne_data, symbol, 'secondary', max_retries=4
        )
        if result:
            logger.success(f"✅ TrendLyne secondary source successful for {symbol}: price={result.get('price')}")
        else:
            logger.warning(f"❌ TrendLyne secondary source failed for {symbol}")
        return result
    
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
    
    def _get_trendlyne_urls(self, symbol: str) -> List[str]:
        """Generate TrendLyne URLs with WORKING 2024 patterns for live data"""
        urls = []
        
        # Priority 1: Direct mapping (most likely to work)
        if symbol in self.trendlyne_symbol_map:
            company_slug = self.trendlyne_symbol_map[symbol]
            urls.extend([
                f"https://trendlyne.com/equity/{company_slug}/",
                f"https://www.trendlyne.com/equity/{company_slug}/",
                f"https://trendlyne.com/equity/{company_slug}",
                f"https://www.trendlyne.com/equity/{company_slug}"
            ])
        
        # Priority 2: Search-based URLs (backup for live data)
        symbol_lower = symbol.lower()
        urls.extend([
            f"https://trendlyne.com/search/{symbol}",
            f"https://www.trendlyne.com/search/{symbol}",
            f"https://trendlyne.com/search?q={symbol}",
            f"https://www.trendlyne.com/search?q={symbol}"
        ])
        
        # Priority 3: Common patterns that might work
        company_patterns = [
            f"{symbol_lower}-limited-{symbol_lower}",
            f"{symbol_lower}-ltd-{symbol_lower}",
            f"{symbol_lower}-{symbol_lower}",
            symbol_lower
        ]
        
        for pattern in company_patterns:
            urls.extend([
                f"https://trendlyne.com/equity/{pattern}/",
                f"https://www.trendlyne.com/equity/{pattern}/",
                f"https://trendlyne.com/stocks/{pattern}/",
                f"https://www.trendlyne.com/stocks/{pattern}/"
            ])
        
        # Priority 4: API endpoints for live data
        urls.extend([
            f"https://api.trendlyne.com/web/v1/equity/{symbol}/",
            f"https://api.trendlyne.com/v1/stocks/{symbol}/",
            f"https://trendlyne.com/api/stocks/{symbol}",
            f"https://www.trendlyne.com/api/equity/{symbol}"
        ])
        
        return urls[:15]  # Limit but allow more attempts for live data

    async def _find_working_url(self, source: str, symbol: str, session) -> Optional[str]:
        """Find working URL with improved live data detection"""
        if source != 'trendlyne':
            return await super()._find_working_url(source, symbol, session)
        
        urls = self._get_trendlyne_urls(symbol)
        logger.info(f"🔍 Searching {len(urls)} TrendLyne URLs for {symbol}")
        
        for i, url in enumerate(urls):
            try:
                logger.debug(f"🌐 Trying TrendLyne URL {i+1}/{len(urls)}: {url}")
                
                # Use HEAD first to check availability quickly
                head_response = await session.head(url, timeout=4, follow_redirects=True)
                
                if head_response.status_code == 200:
                    # Verify with GET to ensure data is available
                    get_response = await session.get(url, timeout=6, follow_redirects=True)
                    if get_response.status_code == 200 and len(get_response.text) > 1000:
                        logger.success(f"✅ Found working TrendLyne URL: {url}")
                        # Quick validation - check if it contains stock-related content
                        content_lower = get_response.text.lower()
                        if any(keyword in content_lower for keyword in ['price', 'stock', 'equity', 'share', 'trading']):
                            logger.success(f"✅ Validated TrendLyne content for {symbol}")
                            return url
                        else:
                            logger.warning(f"⚠️ TrendLyne URL lacks stock content: {url}")
                            continue
                        
                elif head_response.status_code in [301, 302, 303, 307, 308]:
                    # Handle redirects for live data
                    final_url = str(head_response.url)
                    if final_url != url:
                        logger.debug(f"🔄 Following redirect: {url} -> {final_url}")
                        get_response = await session.get(final_url, timeout=6)
                        if get_response.status_code == 200 and len(get_response.text) > 1000:
                            content_lower = get_response.text.lower()
                            if any(keyword in content_lower for keyword in ['price', 'stock', 'equity', 'share', 'trading']):
                                logger.success(f"✅ Found working TrendLyne URL via redirect: {final_url}")
                                return final_url
                
                logger.debug(f"❌ TrendLyne URL {i+1}/{len(urls)} failed: {url} ({head_response.status_code})")
                    
            except asyncio.TimeoutError:
                logger.debug(f"⏰ TrendLyne URL timeout: {url}")
                continue
            except Exception as e:
                logger.debug(f"❌ TrendLyne URL error: {url} - {str(e)[:50]}")
                continue
                
            # Small delay between attempts to avoid rate limiting
            if i < len(urls) - 1:
                await asyncio.sleep(0.2)
        
        logger.warning(f"⚠️ No working TrendLyne URL found for {symbol} after {len(urls)} attempts")
        return None

    async def _fetch_trendlyne_data(self, symbol: str) -> Optional[Dict]:
        """Fetch live data from TrendLyne with enhanced parsing"""
        logger.info(f"🌐 Starting TrendLyne data fetch for {symbol}")
        
        headers = {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0'
        }
        
        # Optimized for live data scraping
        limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
        timeout = httpx.Timeout(10.0, connect=5.0, read=10.0, write=5.0)
        
        try:
            async with httpx.AsyncClient(
                headers=headers, 
                timeout=timeout,
                limits=limits,
                follow_redirects=True,  # Allow automatic redirects for live data
                http2=True  # Enable HTTP/2 for better performance
            ) as session:
                # Find working URL with extended timeout for live data
                logger.debug(f"🔍 Searching for working TrendLyne URL for {symbol}")
                working_url = await asyncio.wait_for(
                    self._find_working_url('trendlyne', symbol, session),
                    timeout=20.0  # More time for live data discovery
                )
                
                if not working_url:
                    logger.warning(f"TrendLyne: No working URL found for {symbol}")
                    return None
                
                logger.debug(f"📡 Fetching live data from: {working_url}")
                
                # Small jitter to appear more human
                await asyncio.sleep(random.uniform(0.1, 0.3))
                
                # Fetch the live data
                response = await session.get(working_url, timeout=10.0)
                
                if response.status_code == 200:
                    html_content = response.text
                    logger.debug(f"📄 Retrieved HTML content: {len(html_content)} characters")
                    
                    # More lenient content validation for live data
                    if len(html_content) < 200:
                        logger.warning(f"TrendLyne: Content too short for {symbol} ({len(html_content)} chars)")
                        return None
                    
                    # Parse the live data
                    logger.debug(f"🔍 Parsing HTML content for {symbol}")
                    data = self._parse_trendlyne_html(html_content, symbol)
                    
                    if data:
                        logger.success(f"TrendLyne: Successfully scraped live data for {symbol} - Price: {data.get('price')}")
                        return data
                    else:
                        # Try alternative parsing for live data
                        logger.debug(f"🔄 Trying alternative parsing for {symbol}")
                        data = self._parse_alternative_formats(html_content, symbol)
                        if data:
                            logger.success(f"TrendLyne: Alternative parsing successful for {symbol} - Price: {data.get('price')}")
                            return data
                        else:
                            logger.warning(f"TrendLyne: Could not parse live data for {symbol}")
                            # Save HTML for debugging (first 1000 chars)
                            logger.debug(f"HTML Preview: {html_content[:1000]}...")
                            return None
                else:
                    logger.warning(f"TrendLyne: HTTP {response.status_code} for {symbol}")
                    return None
                    
        except asyncio.TimeoutError:
            logger.warning(f"TrendLyne: Overall timeout for {symbol}")
            return None
        except Exception as e:
            logger.error(f"TrendLyne: Error fetching live data for {symbol}: {e}")
            return None

    def _parse_trendlyne_html(self, html_content: str, symbol: str) -> Optional[Dict]:
        """Enhanced HTML parsing for live TrendLyne data"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            logger.debug(f"🔍 Parsing HTML for {symbol} with BeautifulSoup")
            
            price = None
            volume = None
            change = None
            change_percent = None
            
            # Enhanced price selectors for live data
            price_selectors = [
                '.current-price', '.stock-price', '.price-current', '.ltp', '.last-price',
                '[data-field="price"]', '[data-field="ltp"]', '[data-field="current_price"]',
                '.quote-price', '.price-ltp', '.stock-ltp', '.live-price',
                'span[class*="price"]', 'div[class*="price"]', '.price',
                '[data-testid="price"]', '[data-cy="price"]',
                # Additional selectors for modern websites
                '.stock-quote-price', '.equity-price', '.market-price',
                '[data-price]', '[aria-label*="price"]', '.real-time-price'
            ]
            
            # Try to find price in various locations
            for selector in price_selectors:
                elements = soup.select(selector)
                logger.debug(f"🎯 Trying selector '{selector}': found {len(elements)} elements")
                for element in elements:
                    price_text = element.get_text(strip=True)
                    logger.debug(f"📝 Price text from '{selector}': '{price_text}'")
                    extracted_price = self._extract_number(price_text)
                    if extracted_price and 1 <= extracted_price <= 500000:  # Broader range for live data
                        price = extracted_price
                        logger.success(f"✅ Found price {price} using selector: {selector}")
                        break
                if price:
                    break
            
            # Enhanced volume selectors
            volume_selectors = [
                '.volume', '.trade-volume', '.vol', '.volume-traded',
                '[data-field="volume"]', '[data-field="trade_volume"]',
                'span[class*="volume"]', 'div[class*="volume"]',
                '[data-testid="volume"]', '[data-cy="volume"]',
                '.trading-volume', '.market-volume'
            ]
            
            for selector in volume_selectors:
                elements = soup.select(selector)
                for element in elements:
                    volume_text = element.get_text(strip=True)
                    extracted_volume = self._extract_volume_number(volume_text)
                    if extracted_volume:
                        volume = extracted_volume
                        logger.debug(f"✅ Found volume {volume} using selector: {selector}")
                        break
                if volume:
                    break
            
            # Look for change data
            change_selectors = [
                '.change', '.price-change', '.change-value',
                '[data-field="change"]', 'span[class*="change"]',
                '.stock-change', '.price-diff'
            ]
            
            for selector in change_selectors:
                elements = soup.select(selector)
                for element in elements:
                    change_text = element.get_text(strip=True)
                    extracted_change = self._extract_number(change_text)
                    if extracted_change is not None:
                        change = extracted_change
                        logger.debug(f"✅ Found change {change} using selector: {selector}")
                        break
                if change is not None:
                    break
            
            # If still no price, try script tags for JSON data
            if not price:
                logger.debug(f"🔄 No price found in HTML elements, trying script tags for {symbol}")
                price = self._extract_price_from_scripts(soup)
                if price:
                    logger.success(f"✅ Found price {price} in script tags")
            
            # If still no price, try meta tags
            if not price:
                logger.debug(f"🔄 No price found in scripts, trying meta tags for {symbol}")
                price = self._extract_price_from_meta(soup)
                if price:
                    logger.success(f"✅ Found price {price} in meta tags")
            
            if price and price > 0:
                result = {
                    'symbol': symbol,
                    'price': price,
                    'volume': volume or 0,
                    'change': change,
                    'change_percent': change_percent,
                    'source': 'trendlyne_live',
                    'timestamp': time.time(),
                    'data_quality': 'high' if volume else 'medium',
                    'scraping_method': 'html_parsing'
                }
                logger.success(f"✅ Successfully parsed TrendLyne data for {symbol}: {result}")
                return result
            else:
                logger.warning(f"❌ No valid price found in HTML for {symbol}")
                # Log some sample HTML for debugging
                sample_text = soup.get_text()[:500] if soup else "No soup"
                logger.debug(f"📄 Sample HTML text: {sample_text}")
                return None
                
        except Exception as e:
            logger.error(f"TrendLyne: Error parsing HTML for {symbol}: {e}")
            return None
    
    def _parse_alternative_formats(self, html_content: str, symbol: str) -> Optional[Dict]:
        """Parse alternative data formats (JSON, embedded data) for live scraping"""
        try:
            # Try to find JSON data in script tags
            soup = BeautifulSoup(html_content, 'html.parser')
            script_tags = soup.find_all('script')
            
            for script in script_tags:
                if script.string:
                    script_content = script.string
                    
                    # Look for JSON-like structures
                    if 'price' in script_content.lower() or 'quote' in script_content.lower():
                        price = self._extract_from_json_like(script_content, symbol)
                        if price:
                            return price
            
            # Try to extract from data attributes
            data_elements = soup.find_all(attrs={'data-price': True})
            for element in data_elements:
                price_text = element.get('data-price')
                price = self._extract_number(price_text)
                if price and 1 <= price <= 500000:
                    return {
                        'symbol': symbol,
                        'price': price,
                        'volume': 0,
                        'source': 'trendlyne_data_attr',
                        'timestamp': time.time(),
                        'data_quality': 'medium',
                        'scraping_method': 'data_attributes'
                    }
            
            return None
            
        except Exception as e:
            logger.debug(f"TrendLyne: Error in alternative parsing for {symbol}: {e}")
            return None
    
    def _extract_from_json_like(self, script_content: str, symbol: str) -> Optional[Dict]:
        """Extract price data from JSON-like structures in scripts"""
        try:
            import re
            import json
            
            # Try to find JSON objects
            json_patterns = [
                r'\{[^{}]*"price"[^{}]*\}',
                r'\{[^{}]*"ltp"[^{}]*\}',
                r'\{[^{}]*"currentPrice"[^{}]*\}',
                r'\{[^{}]*"quote"[^{}]*\}'
            ]
            
            for pattern in json_patterns:
                matches = re.findall(pattern, script_content, re.IGNORECASE)
                for match in matches:
                    try:
                        data = json.loads(match)
                        price = None
                        volume = None
                        
                        # Look for price in various keys
                        for key in ['price', 'ltp', 'currentPrice', 'last', 'close']:
                            if key in data and isinstance(data[key], (int, float, str)):
                                price = self._extract_number(str(data[key]))
                                if price and 1 <= price <= 500000:
                                    break
                        
                        # Look for volume
                        for key in ['volume', 'vol', 'tradeVolume']:
                            if key in data:
                                volume = self._extract_volume_number(str(data[key]))
                                if volume:
                                    break
                        
                        if price:
                            return {
                                'symbol': symbol,
                                'price': price,
                                'volume': volume or 0,
                                'source': 'trendlyne_json',
                                'timestamp': time.time(),
                                'data_quality': 'high',
                                'scraping_method': 'json_extraction'
                            }
                            
                    except json.JSONDecodeError:
                        continue
            
            # Try regex patterns for numeric values
            price_patterns = [
                r'"price"[:\s]*([0-9.]+)',
                r'"ltp"[:\s]*([0-9.]+)',
                r'"currentPrice"[:\s]*([0-9.]+)'
            ]
            
            for pattern in price_patterns:
                match = re.search(pattern, script_content, re.IGNORECASE)
                if match:
                    price = float(match.group(1))
                    if 1 <= price <= 500000:
                        return {
                            'symbol': symbol,
                            'price': price,
                            'volume': 0,
                            'source': 'trendlyne_regex',
                            'timestamp': time.time(),
                            'data_quality': 'medium',
                            'scraping_method': 'regex_extraction'
                        }
            
            return None
            
        except Exception as e:
            logger.debug(f"TrendLyne: Error extracting from JSON-like content: {e}")
            return None
    
    def _extract_price_from_scripts(self, soup) -> Optional[float]:
        """Extract price from script tags"""
        try:
            import re
            script_tags = soup.find_all('script')
            
            for script in script_tags:
                if script.string and ('price' in script.string.lower() or 'quote' in script.string.lower()):
                    # Multiple regex patterns for price extraction
                    patterns = [
                        r'"price"[:\s]*([0-9.]+)',
                        r'"ltp"[:\s]*([0-9.]+)',
                        r'"currentPrice"[:\s]*([0-9.]+)',
                        r'"last"[:\s]*([0-9.]+)',
                        r'price["\']?\s*:\s*([0-9.]+)',
                        r'ltp["\']?\s*:\s*([0-9.]+)'
                    ]
                    
                    for pattern in patterns:
                        match = re.search(pattern, script.string, re.IGNORECASE)
                        if match:
                            price = float(match.group(1))
                            if 1 <= price <= 500000:
                                return price
            
            return None
            
        except Exception as e:
            logger.debug(f"TrendLyne: Error extracting price from scripts: {e}")
            return None
    
    def _extract_price_from_meta(self, soup) -> Optional[float]:
        """Extract price from meta tags"""
        try:
            meta_tags = soup.find_all('meta')
            
            for meta in meta_tags:
                # Check property and name attributes
                for attr in ['property', 'name']:
                    attr_value = meta.get(attr, '').lower()
                    if 'price' in attr_value or 'amount' in attr_value:
                        content = meta.get('content', '')
                        price = self._extract_number(content)
                        if price and 1 <= price <= 500000:
                            return price
            
            return None
            
        except Exception as e:
            logger.debug(f"TrendLyne: Error extracting price from meta tags: {e}")
            return None

    def _extract_number(self, text: str) -> Optional[float]:
        """Enhanced number extraction for live data"""
        if not text:
            return None
        
        try:
            import re
            
            # Remove common prefixes and suffixes
            cleaned = text.replace('₹', '').replace('Rs', '').replace('$', '').replace('INR', '')
            cleaned = cleaned.replace('%', '').strip()
            
            # Handle negative numbers (for changes)
            is_negative = cleaned.startswith('-') or cleaned.startswith('(')
            
            # Extract numeric part with decimals and commas
            number_match = re.search(r'([\d,]+\.?\d*)', cleaned.replace('(', '').replace(')', ''))
            
            if number_match:
                number_str = number_match.group(1).replace(',', '')
                if number_str:
                    result = float(number_str)
                    return -result if is_negative else result
            
            return None
            
        except (ValueError, TypeError, AttributeError):
            return None
    
    def _extract_volume_number(self, text: str) -> Optional[int]:
        """Enhanced volume extraction for live data"""
        if not text:
            return None
        
        try:
            import re
            text_lower = text.lower().strip()
            
            # Extract number part
            number_match = re.search(r'([\d.,]+)', text_lower)
            if not number_match:
                return None
            
            number_str = number_match.group(1).replace(',', '')
            base_number = float(number_str)
            
            # Handle Indian volume units and international units
            if any(unit in text_lower for unit in ['crore', 'cr']):
                return int(base_number * 10000000)  # 1 crore = 10 million
            elif any(unit in text_lower for unit in ['lakh', 'lac', 'l']):
                return int(base_number * 100000)    # 1 lakh = 100 thousand
            elif 'k' in text_lower:
                return int(base_number * 1000)      # 1k = 1000
            elif 'm' in text_lower:
                return int(base_number * 1000000)   # 1m = 1 million
            elif 'b' in text_lower:
                return int(base_number * 1000000000) # 1b = 1 billion
            else:
                return int(base_number)
                
        except (ValueError, TypeError, AttributeError):
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
