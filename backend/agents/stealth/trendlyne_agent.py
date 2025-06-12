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
        # TrendLyne-specific symbol to URL mapping - FIXED with 2024 working patterns
        self.trendlyne_symbol_map = {
            'RELIANCE': 'reliance-industries-ltd',
            'TCS': 'tata-consultancy-services-ltd', 
            'INFY': 'infosys-ltd',
            'HDFC': 'hdfc-bank-ltd',
            'HDFCBANK': 'hdfc-bank-ltd',
            'ICICIBANK': 'icici-bank-ltd',
            'SBIN': 'state-bank-india-ltd',
            'ITC': 'itc-ltd',
            'WIPRO': 'wipro-ltd',
            'MARUTI': 'maruti-suzuki-india-ltd',
            'BHARTIARTL': 'bharti-airtel-ltd',
            'HCLTECH': 'hcl-technologies-ltd',
            'AXISBANK': 'axis-bank-ltd',
            'LT': 'larsen-toubro-ltd',
            'ASIANPAINT': 'asian-paints-ltd',
            'NESTLEIND': 'nestle-india-ltd',
            'ULTRACEMCO': 'ultratech-cement-ltd',
            'KOTAKBANK': 'kotak-mahindra-bank-ltd',
            'BAJFINANCE': 'bajaj-finance-ltd',
            'TITAN': 'titan-company-ltd'
        }
        
        # Circuit breaker settings - More conservative to handle 403/500 errors
        self.circuit_breaker_config = {
            'primary': {'max_failures': 3, 'timeout': 45, 'current_failures': 0, 'last_failure': 0},
            'secondary': {'max_failures': 2, 'timeout': 60, 'current_failures': 0, 'last_failure': 0},
            'tertiary': {'max_failures': 3, 'timeout': 20, 'current_failures': 0, 'last_failure': 0},
            'emergency': {'max_failures': 2, 'timeout': 40, 'current_failures': 0, 'last_failure': 0}
        }
        
        # Rate limiting - More conservative to avoid 403s
        self.last_request_time = 0
        self.min_request_interval = 2.0  # Increased from 0.8 to 2.0 seconds to reduce 403s
        
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
    
    async def _fetch_trendlyne_data(self, symbol: str) -> Optional[Dict]:
        """Fetch live data from TrendLyne with enhanced error handling"""
        logger.info(f"🌐 Starting TrendLyne data fetch for {symbol}")
        
        # Enhanced headers to avoid detection
        headers = {
            'User-Agent': random.choice([
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0'
            ]),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,hi;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'DNT': '1',
            'Sec-GPC': '1'
        }
        
        # More conservative settings to avoid 403s
        limits = httpx.Limits(max_keepalive_connections=2, max_connections=4)
        timeout = httpx.Timeout(8.0, connect=4.0, read=8.0, write=4.0)
        
        try:
            async with httpx.AsyncClient(
                headers=headers, 
                timeout=timeout,
                limits=limits,
                follow_redirects=True,
                http2=False
            ) as session:
                # Find working URL with conservative timeout
                logger.debug(f"🔍 Searching for working TrendLyne URL for {symbol}")
                working_url = await asyncio.wait_for(
                    self._find_working_url('trendlyne', symbol, session),
                    timeout=15.0  # Reduced from 20 to 15 seconds
                )
                
                if not working_url:
                    logger.warning(f"TrendLyne: No working URL found for {symbol}")
                    return None
                
                logger.debug(f"📡 Fetching live data from: {working_url}")
                
                # Add longer jitter to appear more human and avoid rate limiting
                await asyncio.sleep(random.uniform(0.5, 1.5))
                
                # Fetch the live data with retry on rate limiting
                max_retries = 2
                for attempt in range(max_retries):
                    try:
                        response = await session.get(working_url, timeout=8.0)
                        
                        if response.status_code == 200:
                            html_content = response.text
                            logger.debug(f"📄 Retrieved HTML content: {len(html_content)} characters")
                            
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
                                    return None
                                    
                        elif response.status_code == 403:
                            logger.warning(f"TrendLyne: Rate limited (403) for {symbol} - attempt {attempt + 1}")
                            if attempt < max_retries - 1:
                                # Exponential backoff for rate limiting
                                delay = (2 ** attempt) * random.uniform(2.0, 4.0)
                                logger.debug(f"Backing off for {delay:.1f}s due to rate limiting")
                                await asyncio.sleep(delay)
                                continue
                            else:
                                logger.error(f"TrendLyne: Rate limited exhausted retries for {symbol}")
                                return None
                                
                        else:
                            logger.warning(f"TrendLyne: HTTP {response.status_code} for {symbol}")
                            return None
                            
                    except httpx.TimeoutException:
                        logger.warning(f"TrendLyne: Request timeout for {symbol} on attempt {attempt + 1}")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(random.uniform(1.0, 2.0))
                            continue
                        else:
                            return None
                
                return None
                    
        except asyncio.TimeoutError:
            logger.warning(f"TrendLyne: Overall timeout for {symbol}")
            return None
        except Exception as e:
            logger.error(f"TrendLyne: Error fetching live data for {symbol}: {e}")
            return None

    async def _find_working_url(self, source: str, symbol: str, session) -> Optional[str]:
        """Find working URL with improved error handling for 404s and rate limiting"""
        if source != 'trendlyne':
            return await super()._find_working_url(source, symbol, session)
        
        urls = self._get_trendlyne_urls(symbol)
        logger.info(f"🔍 Searching {len(urls)} TrendLyne URLs for {symbol}")
        
        # Add extra delay before starting to avoid rate limiting
        await asyncio.sleep(random.uniform(0.5, 1.0))
        
        for i, url in enumerate(urls):
            try:
                logger.debug(f"🌐 Trying TrendLyne URL {i+1}/{len(urls)}: {url}")
                
                # Use shorter timeout and handle errors better
                get_response = await session.get(url, timeout=4, follow_redirects=True)
                
                if get_response.status_code == 200 and len(get_response.text) > 500:
                    # Quick validation - check if it contains stock-related content
                    content_lower = get_response.text.lower()
                    stock_keywords = ['price', 'stock', 'equity', 'share', 'trading', 'market', 'nse', 'bse']
                    if any(keyword in content_lower for keyword in stock_keywords):
                        logger.success(f"✅ Found working TrendLyne URL: {url}")
                        return url
                    else:
                        logger.debug(f"⚠️ TrendLyne URL lacks stock content: {url}")
                        continue
                        
                elif get_response.status_code == 404:
                    logger.debug(f"❌ TrendLyne URL not found (404): {url}")
                    continue
                    
                elif get_response.status_code == 403:
                    logger.warning(f"🚫 TrendLyne rate limited (403): {url} - backing off")
                    # Increase delay for subsequent requests when rate limited
                    await asyncio.sleep(random.uniform(2.0, 4.0))
                    continue
                    
                elif get_response.status_code >= 500:
                    logger.debug(f"🔥 TrendLyne server error ({get_response.status_code}): {url}")
                    continue
                    
                else:
                    logger.debug(f"❌ TrendLyne URL failed ({get_response.status_code}): {url}")
                    
            except asyncio.TimeoutError:
                logger.debug(f"⏰ TrendLyne URL timeout: {url}")
                continue
            except httpx.ConnectError:
                logger.debug(f"🔌 TrendLyne connection error: {url}")
                continue
            except Exception as e:
                logger.debug(f"❌ TrendLyne URL error: {url} - {str(e)[:50]}")
                continue
                
            # Progressive delay between attempts to avoid rate limiting
            if i < len(urls) - 1:
                delay = min(0.5 + (i * 0.2), 2.0)  # Progressive delay up to 2 seconds
                await asyncio.sleep(delay)
        
        logger.warning(f"⚠️ No working TrendLyne URL found for {symbol} after {len(urls)} attempts")
        return None

    def _get_trendlyne_urls(self, symbol: str) -> List[str]:
        """Generate TrendLyne URLs with CURRENT WORKING 2024 patterns"""
        urls = []
        
        # Priority 1: Updated direct mapping patterns (current TrendLyne structure)
        if symbol in self.trendlyne_symbol_map:
            company_slug = self.trendlyne_symbol_map[symbol]
            urls.extend([
                f"https://trendlyne.com/equity/{company_slug}",
                f"https://www.trendlyne.com/equity/{company_slug}",
                f"https://trendlyne.com/equity/{company_slug}/",
                f"https://www.trendlyne.com/equity/{company_slug}/"
            ])
        
        # Priority 2: Alternative working patterns based on current site structure
        symbol_lower = symbol.lower()
        urls.extend([
            # Current TrendLyne equity patterns
            f"https://trendlyne.com/equity/{symbol_lower}",
            f"https://www.trendlyne.com/equity/{symbol_lower}",
            f"https://trendlyne.com/equity/{symbol_lower}-ltd",
            f"https://www.trendlyne.com/equity/{symbol_lower}-ltd",
            
            # Stock pages
            f"https://trendlyne.com/stock/{symbol_lower}",
            f"https://www.trendlyne.com/stock/{symbol_lower}",
            
            # Company pages
            f"https://trendlyne.com/company/{symbol_lower}",
            f"https://www.trendlyne.com/company/{symbol_lower}",
            
            # Search as last resort (these actually work better than direct URLs)
            f"https://trendlyne.com/search/{symbol}",
            f"https://www.trendlyne.com/search/{symbol}"
        ])
        
        return urls[:10]  # Reduced to 10 URLs for faster processing

    async def _parse_trendlyne_html(self, html_content: str, symbol: str) -> Optional[Dict]:
        """Enhanced HTML parsing with better selectors for current TrendLyne structure"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            logger.debug(f"🔍 Parsing HTML for {symbol} with BeautifulSoup")
            
            price = None
            volume = None
            change = None
            
            # Updated price selectors for current TrendLyne structure
            price_selectors = [
                # Modern TrendLyne selectors
                '.price', '.current-price', '.stock-price', '.ltp', '.last-price',
                '[data-price]', '[data-ltp]', '[data-current-price]',
                '.quote-price', '.live-price', '.market-price',
                
                # Generic selectors that work across sites
                'span[class*="price"]', 'div[class*="price"]',
                'span[class*="ltp"]', 'div[class*="ltp"]',
                '.stock-quote-price', '.equity-price',
                
                # Fallback selectors
                '[data-testid*="price"]', '[data-cy*="price"]',
                '[aria-label*="price"]', '[title*="price"]',
                
                # Text-based searches for price elements
                'span:contains("₹")', 'div:contains("₹")',
                'span:contains("Rs")', 'div:contains("Rs")'
            ]
            
            # Try to find price in various locations
            for selector in price_selectors:
                try:
                    elements = soup.select(selector)
                    logger.debug(f"🎯 Trying selector '{selector}': found {len(elements)} elements")
                    
                    for element in elements:
                        # Get text from element and its immediate children
                        price_text = element.get_text(strip=True)
                        
                        # Also check data attributes
                        for attr in ['data-price', 'data-ltp', 'data-value', 'value']:
                            if element.has_attr(attr):
                                attr_value = element.get(attr)
                                if attr_value and attr_value.replace('.', '').replace(',', '').isdigit():
                                    price_text = attr_value
                                    break
                        
                        logger.debug(f"📝 Price text from '{selector}': '{price_text[:50]}'")
                        extracted_price = self._extract_number(price_text)
                        
                        if extracted_price and 1 <= extracted_price <= 500000:
                            price = extracted_price
                            logger.success(f"✅ Found price {price} using selector: {selector}")
                            break
                            
                except Exception as selector_error:
                    logger.debug(f"Selector '{selector}' failed: {selector_error}")
                    continue
                    
                if price:
                    break
            
            # Enhanced volume search
            if not volume:
                volume_selectors = [
                    '.volume', '.trade-volume', '.vol', '.volume-traded',
                    '[data-volume]', '[data-vol]', '[data-trade-volume]',
                    'span[class*="volume"]', 'div[class*="volume"]',
                    '.trading-volume', '.market-volume'
                ]
                
                for selector in volume_selectors:
                    try:
                        elements = soup.select(selector)
                        for element in elements:
                            volume_text = element.get_text(strip=True)
                            extracted_volume = self._extract_volume_number(volume_text)
                            if extracted_volume:
                                volume = extracted_volume
                                logger.debug(f"✅ Found volume {volume} using selector: {selector}")
                                break
                    except:
                        continue
                    if volume:
                        break
            
            # If still no price, try more aggressive parsing
            if not price:
                logger.debug(f"🔄 No price found in standard selectors, trying aggressive parsing for {symbol}")
                
                # Look for any element containing currency symbols and numbers
                all_text = soup.get_text()
                price = self._extract_price_from_text(all_text, symbol)
                
                if price:
                    logger.success(f"✅ Found price {price} via text parsing")
            
            if price and price > 0:
                result = {
                    'symbol': symbol,
                    'price': price,
                    'volume': volume or 0,
                    'change': change,
                    'source': 'trendlyne_live',
                    'timestamp': time.time(),
                    'data_quality': 'high' if volume else 'medium',
                    'scraping_method': 'html_parsing'
                }
                logger.success(f"✅ Successfully parsed TrendLyne data for {symbol}: {result}")
                return result
            else:
                logger.warning(f"❌ No valid price found in HTML for {symbol}")
                return None
                
        except Exception as e:
            logger.error(f"TrendLyne: Error parsing HTML for {symbol}: {e}")
            return None
    
    def _extract_price_from_text(self, text: str, symbol: str) -> Optional[float]:
        """Extract price from raw text when selectors fail"""
        try:
            import re
            
            # Look for patterns like "₹1234.56" or "Rs 1,234.56" in the text
            patterns = [
                r'₹\s*([\d,]+\.?\d*)',
                r'Rs\.?\s*([\d,]+\.?\d*)',
                r'INR\s*([\d,]+\.?\d*)',
                r'Price[:\s]*₹?\s*([\d,]+\.?\d*)',
                r'LTP[:\s]*₹?\s*([\d,]+\.?\d*)',
                r'Current[:\s]*₹?\s*([\d,]+\.?\d*)',
            ]
            
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    price_str = match.group(1).replace(',', '')
                    try:
                        price = float(price_str)
                        if 1 <= price <= 500000:  # Reasonable price range
                            logger.debug(f"Found price {price} using pattern: {pattern}")
                            return price
                    except ValueError:
                        continue
            
            return None
            
        except Exception as e:
            logger.debug(f"Error in text price extraction: {e}")
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
    
    def _get_trendlyne_urls(self, symbol: str) -> List[str]:
        """Generate TrendLyne URLs with CURRENT WORKING 2024 patterns"""
        urls = []
        
        # Priority 1: Updated direct mapping patterns (current TrendLyne structure)
        if symbol in self.trendlyne_symbol_map:
            company_slug = self.trendlyne_symbol_map[symbol]
            urls.extend([
                f"https://trendlyne.com/equity/{company_slug}",
                f"https://www.trendlyne.com/equity/{company_slug}",
                f"https://trendlyne.com/equity/{company_slug}/",
                f"https://www.trendlyne.com/equity/{company_slug}/"
            ])
        
        # Priority 2: Alternative working patterns based on current site structure
        symbol_lower = symbol.lower()
        urls.extend([
            # Current TrendLyne equity patterns
            f"https://trendlyne.com/equity/{symbol_lower}",
            f"https://www.trendlyne.com/equity/{symbol_lower}",
            f"https://trendlyne.com/equity/{symbol_lower}-ltd",
            f"https://www.trendlyne.com/equity/{symbol_lower}-ltd",
            
            # Stock pages
            f"https://trendlyne.com/stock/{symbol_lower}",
            f"https://www.trendlyne.com/stock/{symbol_lower}",
            
            # Company pages
            f"https://trendlyne.com/company/{symbol_lower}",
            f"https://www.trendlyne.com/company/{symbol_lower}",
            
            # Search as last resort (these actually work better than direct URLs)
            f"https://trendlyne.com/search/{symbol}",
            f"https://www.trendlyne.com/search/{symbol}"
        ])
        
        return urls[:10]  # Reduced to 10 URLs for faster processing

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
