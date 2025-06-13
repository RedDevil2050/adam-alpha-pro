from backend.agents.stealth.advanced_base import AdvancedStealthAgentBase, QuadChannelData
from backend.agents.stealth.advanced_stealth_scraper import BrowserConfig
import httpx
import asyncio
import random
import re
import json
from bs4 import BeautifulSoup
from loguru import logger
from typing import Optional, Dict, List, Any

agent_name = "screener_agent"


class ScreenerAgent(AdvancedStealthAgentBase):
    
    def __init__(self):
        super().__init__()
        self.screener_base_url = "https://www.screener.in"
        logger.info("🚀 Enhanced Screener Agent initialized with quad-channel stealth capabilities")
    
    async def _fetch_primary_source(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch from Screener with quad-channel stealth approach using advanced browser automation"""
        logger.info(f"🔍 Starting quad-channel Screener fetch for {symbol}")
        
        # Try different URL patterns
        urls = [
            f"{self.screener_base_url}/company/{symbol.upper()}",
            f"{self.screener_base_url}/company/{symbol.upper()}/consolidated",
            f"{self.screener_base_url}/search/?q={symbol.upper()}",
            f"{self.screener_base_url}/api/company/{symbol.upper()}"
        ]
        
        # Enhanced quad-channel browser strategies
        if self.browser_enabled:
            selectors = {
                'price': '.number, .current-price, [data-field="price"]',
                'market_cap': 'td:contains("Market Cap") + td, .market-cap',
                'pe_ratio': 'td:contains("P/E") + td, .pe-ratio',
                'book_value': 'td:contains("Book Value") + td',
                'dividend_yield': 'td:contains("Dividend Yield") + td'
            }
            
            try:
                browser_results = await self.stealth_scraper.quad_channel_scrape(urls, selectors)
                
                # Process browser results
                for channel_name, channel_result in browser_results.items():
                    if channel_result.get('success') and channel_result.get('data'):
                        processed_data = self._process_screener_data(channel_result['data'])
                        if processed_data:
                            logger.success(f"✅ Screener browser channel {channel_name} succeeded")
                            return {
                                'success': True,
                                'data': processed_data,
                                'channel': channel_name,
                                'method': 'browser',
                                'browser': channel_result.get('browser')
                            }
                        
            except Exception as e:
                logger.warning(f"⚠️ Browser scraping failed: {e}")
        
        # Fallback to HTTP requests with stealth
        return await self._fetch_with_http_fallback(urls, symbol)
    
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
    
    async def _execute_analysis(self, symbol: str, agent_outputs: dict, fused_data: QuadChannelData) -> Dict:
        """Execute screener-specific fundamental analysis."""
        try:
            # Extract data from fused channels
            price = self._extract_best_price(fused_data)
            financial_data = self._extract_financial_metrics(fused_data)
            
            if not price or price <= 0:
                return self._error_response(symbol, "No valid price data from any channel")
            
            # Calculate screener-specific analysis
            fundamental_score = self._calculate_fundamental_score(financial_data)
            verdict = self._get_screener_verdict(fundamental_score, financial_data)
            confidence = self._calculate_screener_confidence(financial_data, fused_data)
            
            return {
                "symbol": symbol,
                "verdict": verdict,
                "confidence": confidence,
                "value": price,
                "details": {
                    "fundamental_analysis": {
                        "fundamental_score": fundamental_score,
                        "pe_ratio": financial_data.get("pe_ratio"),
                        "market_cap": financial_data.get("market_cap"),
                        "debt_to_equity": financial_data.get("debt_to_equity"),
                        "roe": financial_data.get("roe")
                    },
                    "screener_metrics": {
                        "valuation_grade": self._get_valuation_grade(financial_data),
                        "financial_health": self._assess_financial_health(financial_data),
                        "growth_potential": self._assess_growth_potential(financial_data)
                    },
                    "quad_channel_performance": {
                        "channels_used": fused_data.channels_used,
                        "fusion_confidence": fused_data.fusion_confidence,
                        "validation_score": fused_data.validation_score
                    }
                },
                "error": None,
                "agent_name": agent_name
            }
            
        except Exception as e:
            logger.error(f"❌ Screener analysis error for {symbol}: {e}")
            return self._error_response(symbol, str(e))
    
    def _extract_best_price(self, fused_data: QuadChannelData) -> Optional[float]:
        """Extract the best price from available channels."""
        for channel in ["primary", "secondary", "tertiary", "emergency"]:
            channel_data = getattr(fused_data, channel)
            if channel_data and "price" in channel_data:
                price = channel_data["price"]
                if isinstance(price, (int, float)) and price > 0:
                    return float(price)
        return None
    
    def _extract_financial_metrics(self, fused_data: QuadChannelData) -> Dict:
        """Extract financial metrics from all channels."""
        metrics = {}
        
        for channel in ["primary", "secondary", "tertiary", "emergency"]:
            channel_data = getattr(fused_data, channel)
            if channel_data:
                for metric in ["pe_ratio", "market_cap", "debt_to_equity", "roe"]:
                    if metric in channel_data and channel_data[metric] is not None:
                        metrics[metric] = channel_data[metric]
        
        return metrics
    
    def _calculate_fundamental_score(self, financial_data: Dict) -> float:
        """Calculate fundamental analysis score based on screener metrics."""
        score = 0.5  # Base score
        
        # PE ratio scoring
        pe_ratio = financial_data.get("pe_ratio")
        if pe_ratio:
            if 5 <= pe_ratio <= 15:
                score += 0.2
            elif 15 < pe_ratio <= 25:
                score += 0.1
            elif pe_ratio > 40:
                score -= 0.2
        
        # ROE scoring
        roe = financial_data.get("roe")
        if roe:
            if roe > 20:
                score += 0.2
            elif roe > 15:
                score += 0.15
            elif roe > 10:
                score += 0.1
            elif roe < 5:
                score -= 0.1
        
        # Debt to equity scoring
        debt_to_equity = financial_data.get("debt_to_equity")
        if debt_to_equity is not None:
            if debt_to_equity < 0.3:
                score += 0.1
            elif debt_to_equity > 1.0:
                score -= 0.15
        
        return max(0.0, min(1.0, score))
    
    def _get_screener_verdict(self, fundamental_score: float, financial_data: Dict) -> str:
        """Get verdict based on fundamental analysis."""
        if fundamental_score >= 0.8:
            return "STRONG_BUY"
        elif fundamental_score >= 0.65:
            return "BUY"
        elif fundamental_score >= 0.45:
            return "HOLD"
        else:
            return "WEAK_FUNDAMENTALS"
    
    def _calculate_screener_confidence(self, financial_data: Dict, fused_data: QuadChannelData) -> float:
        """Calculate confidence based on data completeness and quality."""
        base_confidence = 0.6
        
        # Data completeness boost
        key_metrics = ["pe_ratio", "market_cap", "roe", "debt_to_equity"]
        available_metrics = sum(1 for metric in key_metrics if financial_data.get(metric) is not None)
        completeness_boost = (available_metrics / len(key_metrics)) * 0.2
        
        # Quad-channel boost
        quad_boost = len(fused_data.channels_used) * 0.05
        
        return min(1.0, base_confidence + completeness_boost + quad_boost)
    
    def _get_valuation_grade(self, financial_data: Dict) -> str:
        """Assign valuation grade based on PE ratio."""
        pe_ratio = financial_data.get("pe_ratio")
        if not pe_ratio:
            return "Unknown"
        elif pe_ratio < 10:
            return "Undervalued"
        elif pe_ratio < 20:
            return "Fair"
        elif pe_ratio < 30:
            return "Expensive"
        else:
            return "Overvalued"
    
    def _assess_financial_health(self, financial_data: Dict) -> str:
        """Assess overall financial health."""
        debt_to_equity = financial_data.get("debt_to_equity")
        roe = financial_data.get("roe")
        
        if debt_to_equity is not None and debt_to_equity < 0.3 and roe and roe > 15:
            return "Excellent"
        elif debt_to_equity is not None and debt_to_equity < 0.6 and roe and roe > 10:
            return "Good"
        elif debt_to_equity is not None and debt_to_equity > 1.0:
            return "Poor"
        else:
            return "Average"
    
    def _assess_growth_potential(self, financial_data: Dict) -> str:
        """Assess growth potential based on available metrics."""
        roe = financial_data.get("roe")
        
        if roe and roe > 20:
            return "High"
        elif roe and roe > 15:
            return "Medium"
        elif roe and roe > 10:
            return "Low"
        else:
            return "Unknown"
    
    async def _fetch_with_http_fallback(self, urls: List[str], symbol: str) -> Optional[Dict[str, Any]]:
        """Fallback HTTP request method with stealth headers"""
        
        for i, url in enumerate(urls):
            try:
                headers = {
                    'User-Agent': random.choice(self.user_agents),
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Referer': 'https://www.google.com/',
                    'Cache-Control': 'max-age=0'
                }
                
                async with httpx.AsyncClient(
                    timeout=20,
                    follow_redirects=True,
                    headers=headers
                ) as client:
                    
                    # Add random delay to avoid rate limiting
                    await asyncio.sleep(random.uniform(1, 3))
                    
                    response = await client.get(url)
                    
                    if response.status_code == 200:
                        data = self._parse_screener_content(response.text)
                        if data:
                            logger.success(f"✅ HTTP fallback succeeded for {url}")
                            return {
                                'success': True,
                                'data': data,
                                'channel': f'http_{i}',
                                'method': 'http'
                            }
                    elif response.status_code == 503:
                        logger.warning(f"⚠️ Rate limited on {url}, trying next...")
                        await asyncio.sleep(random.uniform(5, 10))
                        continue
                    else:
                        logger.debug(f"HTTP {response.status_code} for {url}")
                        
            except Exception as e:
                logger.warning(f"HTTP request failed for {url}: {e}")
                continue
        
        return None
    
    def _process_screener_data(self, scraped_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process data scraped from browser"""
        processed = {}
        
        try:
            # Extract price
            if scraped_data.get('price'):
                price_text = str(scraped_data['price']).strip()
                price_match = re.search(r'[\d,]+\.?\d*', price_text)
                if price_match:
                    processed['price'] = float(price_match.group().replace(',', ''))
            
            # Extract other fields
            for field in ['market_cap', 'pe_ratio', 'book_value', 'dividend_yield']:
                if scraped_data.get(field):
                    processed[field] = str(scraped_data[field]).strip()
            
        except Exception as e:
            logger.error(f"Error processing scraped data: {e}")
        
        return processed
    
    def _parse_screener_content(self, content: str) -> Dict[str, Any]:
        """Parse Screener HTML content"""
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
            logger.error(f"Error parsing Screener content: {e}")
        
        return data
    
    # ...existing code...


async def run(symbol: str, agent_outputs: dict = {}) -> dict:
    agent = ScreenerAgent()
    return await agent.execute(symbol, agent_outputs=agent_outputs)
