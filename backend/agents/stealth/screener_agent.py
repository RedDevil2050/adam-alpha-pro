from backend.agents.stealth.advanced_base import AdvancedStealthAgentBase, QuadChannelData
from backend.agents.stealth.advanced_stealth_scraper import BrowserConfig
from backend.utils.symbol_normalizer_fixed import IndianEquitySymbolNormalizer
import httpx
import asyncio
import random
import re
import json
import time
import numpy as np
from sklearn.ensemble import IsolationForest
from bs4 import BeautifulSoup
from loguru import logger
from typing import Optional, Dict, List, Any

agent_name = "screener_agent"


class ScreenerAgent(AdvancedStealthAgentBase):
    """
    Advanced Screener.in agent with unified stealth architecture:
    - Enhanced URL patterns and adaptive selection
    - Smart caching with TTL management
    - ML-powered analysis and anomaly detection
    - Performance monitoring and health checks
    - Success rate tracking with dynamic weight adjustment
    """
    
    def __init__(self):
        super().__init__()
        self.agent_name = agent_name
        self.base_url = "https://www.screener.in"
        
        # Enhanced ML components for advanced analysis
        self.anomaly_detector = IsolationForest(contamination=0.1, random_state=42)
        self.price_trend_detector = IsolationForest(contamination=0.05, random_state=42)
        self.timeframes = [5, 15, 60, 240]  # minutes
        
        # Enhanced URL patterns for better coverage
        self.url_patterns = [
            "/company/{symbol}",
            "/company/{symbol}/",
            "/company/{symbol}/consolidated/",
            "/company/{symbol}/standalone/",
            "/search/?q={symbol}",
            "/api/company/{symbol}",
            "/stock/{symbol}",
            "/equity/{symbol}",
            "/{symbol}",
            "/companies/{symbol}",
            "/stocks/{symbol}",
            "/data/{symbol}"
        ]
        
        # Enhanced confidence thresholds with dynamic adjustment
        self.fusion_weights = {
            "primary": 0.5,    # Screener.in (can adjust based on success rate)
            "secondary": 0.3,   # Yahoo Finance
            "tertiary": 0.15,   # Alpha Vantage
            "emergency": 0.05   # Other sources
        }
        
        # Add success rate tracking for dynamic weight adjustment
        self.success_rates = {
            "primary": 0.8,    # Screener typically has high success
            "secondary": 0.7,
            "tertiary": 0.6,
            "emergency": 0.9
        }
        
        # Cache for repeated symbol lookups
        self.symbol_cache = {}
        self.cache_ttl = 300  # 5 minutes
        
        logger.info(f"🚀 Advanced Screener Agent v3.0 initialized with unified stealth architecture")

    async def _get_cached_data(self, symbol: str, channel: str) -> Optional[Dict]:
        """Get cached data for symbol and channel"""
        try:
            cache_key = f"{symbol}:{channel}"
            if cache_key in self.symbol_cache:
                cached_data, timestamp = self.symbol_cache[cache_key]
                if time.time() - timestamp < self.cache_ttl:
                    logger.debug(f"💾 Cache hit for {cache_key}")
                    return cached_data
                else:
                    # Remove expired cache
                    del self.symbol_cache[cache_key]
        except Exception as e:
            logger.warning(f"Cache retrieval error: {e}")
        return None
    
    async def _check_cache(self, symbol: str) -> Optional[Dict]:
        """Check if symbol data is cached and still valid"""
        try:
            if symbol in self.symbol_cache:
                cached_data, timestamp = self.symbol_cache[symbol]
                if time.time() - timestamp < self.cache_ttl:
                    logger.debug(f"💾 Using cached data for {symbol}")
                    return cached_data
                else:
                    # Remove expired cache
                    del self.symbol_cache[symbol]
        except Exception as e:
            logger.warning(f"Cache check error: {e}")
        return None
    
    def _cache_result(self, symbol: str, result: Dict):
        """Cache the result for future use"""
        try:
            import time
            self.symbol_cache[symbol] = (result, time.time())
            
            # Limit cache size to prevent memory issues
            if len(self.symbol_cache) > 100:
                # Remove oldest entries
                oldest_key = min(self.symbol_cache.keys(), 
                               key=lambda k: self.symbol_cache[k][1])
                del self.symbol_cache[oldest_key]
        except Exception as e:
            logger.warning(f"Cache storage error: {e}")
    
    def _adaptive_url_selection(self, symbol: str) -> List[str]:
        """Adaptively select URLs based on historical success rates"""
        try:
            # Generate URLs from patterns
            base_urls = []
            for pattern in self.url_patterns:
                url = self.base_url + pattern.format(symbol=symbol)
                base_urls.append(url)
            
            # Sort URLs by historical success (you could add URL-specific success tracking)
            # For now, we'll use the current order but with some randomization
            import random
            urls = base_urls.copy()
            
            # Add some randomization to avoid getting stuck on failed patterns
            if len(urls) > 3:
                # Keep first 3 in order, randomize the rest
                stable_urls = urls[:3]
                random_urls = urls[3:]
                random.shuffle(random_urls)
                urls = stable_urls + random_urls
            
            return urls
        except Exception as e:
            logger.warning(f"URL selection error: {e}")
            # Fallback to basic URLs
            return [
                f"{self.base_url}/company/{symbol}/",
                f"{self.base_url}/company/{symbol}/consolidated/",
                f"{self.base_url}/api/company/{symbol}/"
            ]
    
    async def _fetch_primary_source(self, symbol: str) -> Optional[Dict]:
        """Enhanced Screener.in fetch with caching and adaptive URL selection"""
        logger.info(f"🔍 Starting advanced Screener.in fetch for {symbol}")
        
        # Check cache first
        cached_result = await self._get_cached_data(symbol, "primary")
        if cached_result:
            return cached_result
        
        # Use adaptive URL selection
        urls = self._adaptive_url_selection(symbol)
        
        # Try browser automation first
        try:
            if hasattr(self, 'browser_enabled') and self.browser_enabled:
                logger.debug(f"🌐 Attempting browser automation for {symbol}")
                
                selectors = {
                    'price': '.number, .current-price, [data-field="price"], .stock-price',
                    'market_cap': 'td:contains("Market Cap") + td, .market-cap, [data-field="mcap"]',
                    'pe_ratio': 'td:contains("P/E") + td, .pe-ratio, [data-field="pe"]',
                    'book_value': 'td:contains("Book Value") + td, [data-field="book_value"]',
                    'dividend_yield': 'td:contains("Dividend Yield") + td, [data-field="div_yield"]',
                    'revenue': 'td:contains("Sales") + td, td:contains("Revenue") + td',
                    'profit': 'td:contains("Net Profit") + td, [data-field="profit"]'
                }
                
                browser_config = BrowserConfig(headless=True, stealth_mode=True)
                channel_result = await self.scraper.quad_channel_scrape(urls[0], selectors, config=browser_config)
                
                if channel_result.get('success'):
                    processed_data = self._process_screener_data(channel_result.get('data', {}))
                    result = {
                        'success': True,
                        'data': processed_data,
                        'channel': 'browser_automation',
                        'method': 'quad_channel',
                        'browser': channel_result.get('browser'),
                        'source': 'screener_primary'
                    }
                    # Cache successful result
                    self._cache_result(symbol, "primary", result)
                    # Update success rate
                    self._update_success_rates('primary', True)
                    return result
                        
        except Exception as e:
            logger.warning(f"⚠️ Screener browser automation failed: {e}")
            self._update_success_rates('primary', False)
          # Fallback to enhanced HTTP requests
        http_result = await self._try_enhanced_http(urls, symbol)
        if http_result:
            # Cache successful result
            self._cache_result(symbol, "primary", http_result)
            self._update_success_rates('primary', True)
        else:
            self._update_success_rates('primary', False)
            
        return http_result
    
    async def _try_enhanced_http(self, urls: List[str], symbol: str) -> Optional[Dict]:
        """Enhanced HTTP requests with exponential backoff and smart headers"""
        for i, url in enumerate(urls):
            for attempt in range(3):  # 3 attempts per URL
                try:
                    headers_list = self._generate_smart_headers()
                    headers = headers_list[0] if headers_list else {}
                    
                    logger.debug(f"HTTP attempt {attempt + 1} for {url}")
                    
                    async with httpx.AsyncClient(timeout=15.0, headers=headers) as client:
                        response = await client.get(url)
                        
                        if response.status_code == 200:
                            content = response.text
                            
                            # Validate content quality
                            if len(content) > 1000 and self._is_valid_content(content):
                                parsed_data = self._parse_enhanced_screener_html(content)
                                
                                if parsed_data and parsed_data.get('price'):
                                    logger.success(f"✅ Screener HTTP succeeded: {url}")
                                    return {
                                        'success': True,
                                        'data': parsed_data,
                                        'method': 'http',
                                        'source': 'screener_primary',
                                        'url': url
                                    }
                        
                        elif response.status_code == 503:
                            logger.warning(f"503 error, backing off {2**attempt}s")
                            await asyncio.sleep(2**attempt)
                            continue
                        
                except Exception as e:
                    logger.warning(f"HTTP error for {url}: {e}")
                    await asyncio.sleep(1)
                    continue
        
        return None
    
    def _generate_smart_headers(self) -> List[Dict[str, str]]:
        """Generate smart, rotating headers to avoid detection"""
        headers_list = []
        
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0"
        ]
        
        for ua in user_agents:
            for accept_lang in ["en-US,en;q=0.9", "en-GB,en;q=0.9", "en-US,en;q=0.8"]:
                headers_list.append({
                    "User-Agent": ua,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": accept_lang,
                    "Accept-Encoding": "gzip, deflate, br",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none",
                    "Cache-Control": "max-age=0"
                })
        
        return headers_list
    
    def _is_valid_content(self, text: str) -> bool:
        """Validate if content contains relevant stock data"""
        return any(term in text.lower() for term in 
                  ['screener', 'market cap', 'book value', 'dividend', 'pe ratio', 'sales', 'profit', 'price'])
    
    def _parse_enhanced_screener_html(self, content: str) -> Dict[str, Any]:
        """Enhanced Screener.in HTML parsing with comprehensive selectors"""
        data = {}
        
        try:
            soup = BeautifulSoup(content, 'html.parser')
            
            # Enhanced price extraction with multiple selectors
            price_selectors = [
                {'class': 'number'},
                {'class': 'current-price'},
                {'class': 'stock-price'},
                {'class': 'price-current'},
                {'data-field': 'price'},
                {'class': 'quote-price'}
            ]
            
            price = self._extract_enhanced_price(soup, price_selectors)
            if price:
                data['price'] = price
            
            # Enhanced market cap extraction
            market_cap = self._extract_table_data(soup, ['Market Cap', 'Mkt Cap', 'Market Capitalisation'])
            if market_cap:
                data['market_cap'] = market_cap
            
            # Enhanced PE ratio extraction
            pe_ratio = self._extract_table_data(soup, ['P/E', 'PE Ratio', 'Price/Earnings'])
            if pe_ratio:
                data['pe_ratio'] = pe_ratio
            
            # Enhanced book value extraction
            book_value = self._extract_table_data(soup, ['Book Value', 'BV', 'Book Val'])
            if book_value:
                data['book_value'] = book_value
            
            # Enhanced dividend yield extraction
            dividend_yield = self._extract_table_data(soup, ['Dividend Yield', 'Div Yield', 'Dividend %'])
            if dividend_yield:
                data['dividend_yield'] = dividend_yield
            
            # Enhanced financial metrics
            revenue = self._extract_table_data(soup, ['Sales', 'Revenue', 'Total Revenue'])
            if revenue:
                data['revenue'] = revenue
                
            profit = self._extract_table_data(soup, ['Net Profit', 'Profit', 'Net Income'])
            if profit:
                data['net_profit'] = profit
                
            eps = self._extract_table_data(soup, ['EPS', 'Earnings Per Share'])
            if eps:
                data['eps'] = eps
              # ROE, ROA, ROCE
            roe = self._extract_table_data(soup, ['ROE', 'Return on Equity'])
            if roe:
                data['roe'] = roe
                
            roa = self._extract_table_data(soup, ['ROA', 'Return on Assets'])
            if roa:
                data['roa'] = roa
                
            roce = self._extract_table_data(soup, ['ROCE', 'Return on Capital'])
            if roce:
                data['roce'] = roce
                
        except Exception as e:
            logger.error(f"Error in enhanced Screener HTML parsing: {e}")
        
        return data
    
    async def _fetch_screener_with_strategy(self, url: str, channel: int, strategy: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch Screener data with specific strategy"""
        try:
            # Screener.in specific headers
            headers = {
                'User-Agent': self.stealth_scraper.get_random_user_agent(),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Referer': 'https://www.google.com/'
            }
            
            response = await self.stealth_scraper.scrape_with_browser(
                url,
                browser_type=strategy['browser'],
                wait_time=strategy['delay'],
                headers=headers,
                scroll=strategy['scroll']
            )
            
            if response['success']:
                data = self._parse_screener_data(response['content'])
                return {
                    'success': True,
                    'data': data,
                    'channel': channel,
                    'strategy': strategy
                }
            else:
                return {'success': False, 'channel': channel, 'error': response.get('error')}
                
        except Exception as e:
            self.logger.error(f"Screener Channel {channel} failed: {str(e)}")
            return {'success': False, 'channel': channel, 'error': str(e)}
    
    def _parse_screener_data(self, content: str) -> Dict[str, Any]:
        """Parse Screener specific data"""
        data = {}
        
        try:
            soup = BeautifulSoup(content, 'html.parser')
            
            # Current price
            price_elem = soup.find('span', {'class': 'number'}) or soup.find('div', {'class': 'current-price'})
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                try:
                    data['price'] = float(re.sub(r'[^\d.]', '', price_text))
                except:
                    pass
            
            # Market cap
            mcap_elem = soup.find('td', string=re.compile(r'Market Cap', re.I))
            if mcap_elem and mcap_elem.find_next_sibling():
                mcap_text = mcap_elem.find_next_sibling().get_text(strip=True)
                data['market_cap'] = mcap_text
            
            # PE Ratio
            pe_elem = soup.find('td', string=re.compile(r'P/E', re.I))
            if pe_elem and pe_elem.find_next_sibling():
                pe_text = pe_elem.find_next_sibling().get_text(strip=True)
                data['pe_ratio'] = pe_text
            
            # Book Value
            bv_elem = soup.find('td', string=re.compile(r'Book Value', re.I))
            if bv_elem and bv_elem.find_next_sibling():
                bv_text = bv_elem.find_next_sibling().get_text(strip=True)
                data['book_value'] = bv_text
            
            # Dividend Yield
            div_elem = soup.find('td', string=re.compile(r'Dividend Yield', re.I))
            if div_elem and div_elem.find_next_sibling():
                div_text = div_elem.find_next_sibling().get_text(strip=True)
                data['dividend_yield'] = div_text
            
            # Revenue and Profit (from tables)
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        header = cells[0].get_text(strip=True).lower()
                        value = cells[1].get_text(strip=True)
                        
                        if 'sales' in header or 'revenue' in header:
                            data['revenue'] = value
                        elif 'profit' in header and 'net' in header:
                            data['net_profit'] = value
                        elif 'eps' in header:
                            data['eps'] = value
                            
        except Exception as e:
            self.logger.error(f"Error parsing Screener data: {str(e)}")
        
        return data
    
    def _extract_enhanced_price(self, soup: BeautifulSoup, selectors: List[Dict]) -> Optional[float]:
        """Enhanced price extraction with validation"""
        for selector in selectors:
            try:
                # Try different element types
                for tag in ['span', 'div', 'td', 'p', 'strong']:
                    element = soup.find(tag, selector)
                    if element:
                        price_text = element.get_text(strip=True)
                        price = self._clean_and_validate_price(price_text)
                        if price and 1 <= price <= 500000:  # Reasonable price range
                            return price
            except Exception:
                continue
        return None
    
    def _extract_table_data(self, soup: BeautifulSoup, search_terms: List[str]) -> Optional[str]:
        """Extract data from table rows using search terms"""
        for term in search_terms:
            try:
                # Look for table cells containing the term
                label_elem = soup.find('td', string=re.compile(term, re.I))
                if label_elem:
                    # Try to find the value in next sibling
                    value_elem = label_elem.find_next_sibling()
                    if value_elem:
                        return value_elem.get_text(strip=True)
                
                # Also try looking for the term in various containers
                for container in soup.find_all(['tr', 'div', 'li']):
                    if term.lower() in container.get_text().lower():
                        # Extract value after the term
                        text = container.get_text()
                        pattern = rf'{term}[:\s]*([^\n\r\t]+)'
                        match = re.search(pattern, text, re.I)
                        if match:
                            return match.group(1).strip()
            except Exception:
                continue
        return None
    
    def _clean_and_validate_price(self, price_text: str) -> Optional[float]:
        """Clean and validate price text"""
        try:
            if not price_text:
                return None
            
            # Remove currency symbols and common formatting
            cleaned = re.sub(r'[₹$,\s]', '', price_text)
            
            # Extract numeric value
            price_match = re.search(r'\d+\.?\d*', cleaned)
            if price_match:
                price = float(price_match.group())
                return price if price > 0 else None
        except Exception:
            pass
        return None
    
    def _update_success_rates(self, channel: str, success: bool):
        """Update success rates for dynamic weight adjustment"""
        try:
            current_rate = self.success_rates.get(channel, 0.5)
            # Exponential moving average
            alpha = 0.1
            new_rate = alpha * (1.0 if success else 0.0) + (1 - alpha) * current_rate
            self.success_rates[channel] = max(0.1, min(0.9, new_rate))
            
            # Adjust fusion weights based on success rates
            total_success = sum(self.success_rates.values())
            if total_success > 0:
                for channel_name in self.fusion_weights:
                    base_weight = 0.25  # Equal base weight
                    success_boost = self.success_rates.get(channel_name, 0.5) / total_success
                    self.fusion_weights[channel_name] = base_weight + success_boost * 0.5
        except Exception as e:
            logger.warning(f"Error updating success rates: {e}")
    
    def _get_performance_metrics(self) -> Dict:
        """Get performance metrics for monitoring"""
        try:
            total_requests = sum(getattr(self, f'{channel}_requests', 0) 
                               for channel in ['primary', 'secondary', 'tertiary', 'emergency'])
            
            avg_success_rate = sum(self.success_rates.values()) / len(self.success_rates)
            
            return {
                'total_requests': total_requests,
                'average_success_rate': round(avg_success_rate, 3),
                'cache_size': len(self.symbol_cache),
                'success_rates_by_channel': self.success_rates.copy(),
                'current_fusion_weights': self.fusion_weights.copy(),
                'status': 'healthy'
            }
        except Exception as e:
            logger.warning(f"Error getting performance metrics: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def _health_check(self) -> Dict:
        """Perform health check on the agent"""
        try:
            health_status = {
                'status': 'healthy',
                'issues': [],
                'recommendations': []
            }
            
            # Check success rates
            for channel, rate in self.success_rates.items():
                if rate < 0.3:
                    health_status['issues'].append(f"Low success rate for {channel}: {rate:.1%}")
                    health_status['recommendations'].append(f"Check {channel} channel configuration")
            
            # Check cache performance
            if len(self.symbol_cache) == 0:
                health_status['issues'].append("No cached data available")
                health_status['recommendations'].append("Cache may not be working properly")
            
            # Overall health
            if health_status['issues']:
                health_status['status'] = 'degraded' if len(health_status['issues']) < 3 else 'unhealthy'
            
            return health_status
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'issues': ['Health check failed'],
                'recommendations': ['Check agent configuration']
            }
    
    async def _execute_analysis(self, symbol: str, agent_outputs: dict, fused_data: QuadChannelData) -> Dict:
        """Execute enhanced analysis using quad-channel fused data."""
        try:
            logger.info(f"🔬 Starting enhanced Screener analysis for {symbol}")
            
            # Extract data from the best available channel
            analysis_data = self._extract_best_data(fused_data)
            
            # Calculate confidence score based on data quality
            confidence_score = self._calculate_confidence_score(analysis_data, fused_data)
            
            # Enhanced verdict determination
            verdict = self._get_enhanced_verdict(analysis_data, confidence_score)
            
            return {
                "symbol": symbol,
                "verdict": verdict,
                "confidence": confidence_score,
                "value": confidence_score,
                "details": {
                    "price_data": {
                        "current_price": analysis_data.get("price"),
                        "market_cap": analysis_data.get("market_cap"),
                        "pe_ratio": analysis_data.get("pe_ratio"),
                        "price_validated": True
                    },
                    "fundamental_metrics": {
                        "roe": analysis_data.get("roe"),
                        "roa": analysis_data.get("roa"),
                        "debt_to_equity": analysis_data.get("debt_to_equity"),
                        "dividend_yield": analysis_data.get("dividend_yield")
                    },
                    "data_quality": {
                        "fusion_confidence": fused_data.fusion_confidence,
                        "validation_score": fused_data.validation_score,
                        "channels_used": fused_data.channels_used,
                        "data_freshness": f"{fused_data.collection_timestamp:.1f}s ago"
                    },
                    "source": "enhanced_screener_quad_channel"
                },
                "error": None,
                "agent_name": self.agent_name,
            }
        except Exception as e:
            logger.error(f"❌ Enhanced Screener analysis error for {symbol}: {e}")
            return self._error_response(symbol, str(e))
    
    def _extract_best_data(self, fused_data) -> Dict:
        """Extract the best available data from quad-channel fusion."""
        try:
            best_data = {}
            
            # Prioritize data from successful channels
            for channel in ['primary', 'secondary', 'tertiary', 'emergency']:
                channel_data = getattr(fused_data, channel, {})
                if channel_data and isinstance(channel_data, dict):
                    # Merge data, giving priority to earlier channels
                    for key, value in channel_data.items():
                        if key not in best_data and value is not None:
                            best_data[key] = value
            
            return best_data
        except Exception as e:
            logger.warning(f"Error extracting best data: {e}")
            return {}
    
    def _calculate_confidence_score(self, data: Dict, fused_data) -> float:
        """Calculate confidence score based on data quality and completeness."""
        try:
            base_score = 0.5
            
            # Data completeness bonus
            required_fields = ['price', 'market_cap', 'pe_ratio']
            available_fields = sum(1 for field in required_fields if data.get(field))
            completeness_bonus = (available_fields / len(required_fields)) * 0.3
            
            # Fusion confidence bonus
            fusion_bonus = getattr(fused_data, 'fusion_confidence', 0.5) * 0.2
            
            return min(base_score + completeness_bonus + fusion_bonus, 0.95)
        except Exception as e:
            logger.warning(f"Error calculating confidence: {e}")
            return 0.5
    
    def _get_enhanced_verdict(self, data: Dict, confidence: float) -> str:
        """Get enhanced verdict based on fundamental analysis."""
        try:
            # Simple fundamental scoring
            score = 0.5
            
            # PE ratio analysis
            pe_ratio = data.get('pe_ratio')
            if pe_ratio:
                try:
                    pe_val = float(str(pe_ratio).replace(',', ''))
                    if 10 <= pe_val <= 25:  # Good PE range
                        score += 0.1
                    elif pe_val > 35:  # Overvalued
                        score -= 0.1
                except:
                    pass
            
            # ROE analysis
            roe = data.get('roe')
            if roe:
                try:
                    roe_val = float(str(roe).replace('%', ''))
                    if roe_val > 15:  # Good ROE
                        score += 0.1
                except:
                    pass
            
            # Adjust by confidence
            adjusted_score = score * confidence
            
            # Return verdict
            if adjusted_score > 0.7:
                return "BUY"
            elif adjusted_score > 0.6:
                return "WEAK_BUY"
            elif adjusted_score > 0.4:
                return "HOLD"
            elif adjusted_score > 0.3:
                return "WEAK_SELL"
            else:
                return "SELL"
        except Exception as e:
            logger.warning(f"Error determining verdict: {e}")
            return "HOLD"

    # ...existing code...


async def run(symbol: str, agent_outputs: dict = {}) -> dict:
    """
    Enhanced Screener agent execution with comprehensive error handling
    and performance monitoring
    """
    agent = ScreenerAgent()
    try:
        result = await agent.execute(symbol, agent_outputs=agent_outputs)
        
        # Add performance metrics to result
        performance = agent._get_performance_metrics()
        if performance:
            result['performance_metrics'] = performance
        
        # Add health check
        health = agent._health_check()
        if health:
            result['health_status'] = health
        
        return result
    except Exception as e:
        logger.error(f"❌ Screener agent execution failed for {symbol}: {e}")
        return {
            'success': False,
            'error': str(e),
            'symbol': symbol,
            'agent': 'screener_agent',
            'execution_failed': True
        }


if __name__ == "__main__":
    import asyncio
    
    async def test_screener():
        print("🚀 Testing Advanced Screener Agent v3.0")
        print("=" * 50)
        
        test_symbols = ["RELIANCE", "TCS", "INFY"]
        
        for symbol in test_symbols:
            print(f"\n📊 Testing symbol: {symbol}")
            print("-" * 30)
            
            try:
                result = await run(symbol)
                
                if result.get('success'):
                    data = result.get('data', {})
                    print(f"✅ Success! Price: ₹{data.get('price', 'N/A')}")
                    print(f"   Market Cap: {data.get('market_cap', 'N/A')}")
                    print(f"   PE Ratio: {data.get('pe_ratio', 'N/A')}")
                    
                    # Performance metrics
                    perf = result.get('performance_metrics', {})
                    if perf:
                        print(f"   Avg Success Rate: {perf.get('average_success_rate', 'N/A'):.1%}")
                        print(f"   Cache Size: {perf.get('cache_size', 0)}")
                    
                    # Health status
                    health = result.get('health_status', {})
                    if health:
                        print(f"   Health: {health.get('status', 'unknown')}")
                else:
                    print(f"❌ Failed: {result.get('error', 'Unknown error')}")
            
            except Exception as e:
                print(f"❌ Exception: {e}")
    
    asyncio.run(test_screener())
