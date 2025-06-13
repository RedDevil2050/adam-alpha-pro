import asyncio
from typing import Dict, Any, Optional
from backend.agents.stealth.advanced_base import AdvancedStealthAgentBase
from bs4 import BeautifulSoup
import re
import json

class YahooFinanceAgent(AdvancedStealthAgentBase):
    def __init__(self):
        super().__init__()
        self.base_url = "https://finance.yahoo.com"
        
    async def _fetch_primary_source(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch from Yahoo Finance with quad-channel stealth approach"""
        url = f"{self.base_url}/quote/{symbol.upper()}"
        self.logger.info(f"Trying Yahoo Finance URL: {url}")
        
        # Use quad-channel approach with different strategies
        tasks = []
        strategies = [
            {'browser': 'chrome', 'method': 'selenium', 'proxy': 0},
            {'browser': 'firefox', 'method': 'selenium', 'proxy': 1},
            {'browser': 'chrome', 'method': 'requests', 'proxy': 2},
            {'browser': 'firefox', 'method': 'playwright', 'proxy': 3}
        ]
        
        for i, strategy in enumerate(strategies):
            tasks.append(self._fetch_with_strategy(url, i, strategy))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Return first successful result
        for result in results:
            if isinstance(result, dict) and result.get('success'):
                return result
        
        return None
    
    async def _fetch_with_strategy(self, url: str, channel: int, strategy: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch data using specific strategy"""
        try:
            if strategy['method'] == 'selenium':
                response = await self.stealth_scraper.scrape_with_browser(
                    url, 
                    browser_type=strategy['browser'],
                    proxy_rotation=strategy['proxy']
                )
            elif strategy['method'] == 'playwright':
                response = await self.stealth_scraper.scrape_with_playwright(
                    url,
                    browser_type=strategy['browser']
                )
            else:  # requests
                response = await self.stealth_scraper.scrape_with_requests(url)
            
            if response['success']:
                soup = BeautifulSoup(response['content'], 'html.parser')
                data = self._parse_yahoo_data(soup, response['content'])
                return {
                    'success': True,
                    'data': data,
                    'channel': channel,
                    'strategy': strategy
                }
            else:
                return {'success': False, 'channel': channel, 'error': response.get('error')}
                
        except Exception as e:
            self.logger.error(f"Channel {channel} strategy {strategy} failed: {str(e)}")
            return {'success': False, 'channel': channel, 'error': str(e)}
    
    def _parse_yahoo_data(self, soup: BeautifulSoup, raw_content: str) -> Dict[str, Any]:
        """Parse Yahoo Finance specific data"""
        data = {}
        
        try:
            # Try to extract from JSON in script tags first
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string and 'QuoteSummaryStore' in script.string:
                    try:
                        json_str = script.string
                        start = json_str.find('"QuoteSummaryStore":')
                        if start != -1:
                            start = json_str.find('{', start)
                            end = json_str.find(',"isPending"', start)
                            if end != -1:
                                json_data = json.loads(json_str[start:end+1])
                                quote_data = json_data.get('QuoteSummaryStore', {}).get('price', {})
                                if quote_data:
                                    data['price'] = quote_data.get('regularMarketPrice', {}).get('raw')
                                    data['change'] = quote_data.get('regularMarketChange', {}).get('raw')
                                    data['change_percent'] = quote_data.get('regularMarketChangePercent', {}).get('raw')
                                    data['volume'] = quote_data.get('regularMarketVolume', {}).get('raw')
                                    break
                    except:
                        continue
            
            # Fallback to HTML parsing
            if not data.get('price'):
                price_elem = soup.find('fin-streamer', {'data-field': 'regularMarketPrice'})
                if price_elem:
                    data['price'] = float(price_elem.get('value', 0))
                
                change_elem = soup.find('fin-streamer', {'data-field': 'regularMarketChange'})
                if change_elem:
                    data['change'] = float(change_elem.get('value', 0))
                
                volume_elem = soup.find('fin-streamer', {'data-field': 'regularMarketVolume'})
                if volume_elem:
                    data['volume'] = int(volume_elem.get('value', 0))
                
        except Exception as e:
            self.logger.error(f"Error parsing Yahoo Finance data: {str(e)}")
        
        return data