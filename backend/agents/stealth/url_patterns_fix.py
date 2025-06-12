# URL Patterns Fix for Stealth Agents
# This file contains updated working URL patterns for major Indian finance websites

from typing import Dict, List, Optional
import asyncio
import httpx
import random
from loguru import logger

class SiteURLUpdater:
    """Utility class to find working URL patterns for finance websites"""
    
    def __init__(self):
        self.test_symbols = ["RELIANCE", "TCS", "INFY", "HDFC", "SBIN"]
        
        # Updated URL patterns based on 2024 website structures
        self.updated_patterns = {
            "trendlyne": {
                "base_domains": [
                    "https://trendlyne.com",
                    "https://www.trendlyne.com"
                ],
                "patterns": [
                    "/equity/{symbol}/",
                    "/equity/{symbol}",
                    "/stocks/{symbol}/",
                    "/stocks/{symbol}",
                    "/equity/{company_slug}/",
                    "/equity/{company_slug}",
                ],
                "fallback_patterns": [
                    "/search?q={symbol}",
                    "/search/{symbol}",
                    "/{symbol}"
                ]
            },
            
            "moneycontrol": {
                "base_domains": [
                    "https://www.moneycontrol.com",
                    "https://moneycontrol.com"
                ],
                "patterns": [
                    "/india/stockpricequote/{symbol}",
                    "/stocks/company_info/stock_comp_result.php?sc_id={symbol}",
                    "/stocks/marketstats/indexcomp.php?optex=NSE&opttopic=indexcomp&index=9",
                    "/stocks/fno/marketstats/futures.php?optex=NSE&opttopic=futures&symbol={symbol}",
                    "/shares-stock-price/{symbol}",
                    "/stock-price/{symbol}",
                    "/equity/{symbol}"
                ],
                "fallback_patterns": [
                    "/search/all?search={symbol}",
                    "/search?q={symbol}"
                ]
            },
            
            "tickertape": {
                "base_domains": [
                    "https://www.tickertape.in",
                    "https://tickertape.in"
                ],
                "patterns": [
                    "/stocks/{symbol}",
                    "/stocks/{symbol}/",
                    "/stocks/{symbol}/overview",
                    "/equity/{symbol}",
                    "/equity/{symbol}/",
                    "/screener/equity/{symbol}",
                    "/stock/{symbol}"
                ],
                "fallback_patterns": [
                    "/search?q={symbol}",
                    "/stocks?search={symbol}"
                ]
            },
            
            "yahoo_finance": {
                "base_domains": [
                    "https://finance.yahoo.com",
                    "https://in.finance.yahoo.com"
                ],
                "patterns": [
                    "/quote/{symbol}.NS",
                    "/quote/{symbol}.BO",
                    "/quote/{symbol}",
                    "/lookup?s={symbol}",
                    "/screener/predefined/day_gainers?s={symbol}"
                ],
                "api_patterns": [
                    "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}.NS",
                    "https://query2.finance.yahoo.com/v10/finance/quoteSummary/{symbol}.NS"
                ]
            }
        }
        
        # Symbol mappings for TrendLyne (updated based on current site structure)
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

    async def test_site_patterns(self, site: str, symbol: str = "RELIANCE") -> List[str]:
        """Test URL patterns for a site and return working ones"""
        working_urls = []
        
        if site not in self.updated_patterns:
            logger.warning(f"No patterns defined for site: {site}")
            return working_urls
            
        site_config = self.updated_patterns[site]
        
        # Enhanced headers to avoid bot detection
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-CH-UA": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            "Sec-CH-UA-Mobile": "?0",
            "Sec-CH-UA-Platform": '"Windows"'
        }
        
        async with httpx.AsyncClient(
            timeout=15, 
            follow_redirects=True,
            headers=headers
        ) as client:
            
            for domain in site_config["base_domains"]:
                for pattern in site_config["patterns"]:
                    # Handle special cases for symbol mapping
                    if site == "trendlyne" and symbol in self.trendlyne_symbol_map:
                        company_slug = self.trendlyne_symbol_map[symbol]
                        url = domain + pattern.format(symbol=symbol, company_slug=company_slug)
                    else:
                        url = domain + pattern.format(symbol=symbol)
                    
                    try:
                        logger.info(f"Testing {site} URL: {url}")
                        
                        # Add random delay to avoid rate limiting
                        await asyncio.sleep(random.uniform(0.5, 2.0))
                        
                        response = await client.get(url, timeout=10)
                        
                        if response.status_code == 200:
                            # Additional validation - check content length and common indicators
                            content = response.text
                            if len(content) > 1000 and 'stock' in content.lower():
                                working_urls.append(url)
                                logger.success(f"✅ Working URL found: {url}")
                            else:
                                logger.warning(f"⚠️ URL returns 200 but content seems invalid: {url}")
                        
                        elif response.status_code in [301, 302, 303, 307, 308]:
                            logger.info(f"🔄 Redirect detected for: {url}")
                            # The httpx client should follow redirects automatically
                            
                        elif response.status_code == 404:
                            logger.debug(f"❌ Not found: {url}")
                            
                        elif response.status_code == 403:
                            logger.warning(f"🚫 Forbidden (possible bot detection): {url}")
                            
                        elif response.status_code == 503:
                            logger.warning(f"⚠️ Service unavailable: {url}")
                            
                        else:
                            logger.debug(f"📊 Status {response.status_code}: {url}")
                            
                    except httpx.TimeoutException:
                        logger.debug(f"⏰ Timeout: {url}")
                    except httpx.ConnectError:
                        logger.debug(f"🔌 Connection error: {url}")
                    except Exception as e:
                        logger.debug(f"❌ Error testing {url}: {e}")
        
        return working_urls

    async def update_all_patterns(self) -> Dict[str, List[str]]:
        """Test and update patterns for all sites"""
        results = {}
        
        for site in self.updated_patterns.keys():
            logger.info(f"🔍 Testing patterns for {site}")
            working_urls = await self.test_site_patterns(site)
            results[site] = working_urls
            
            if working_urls:
                logger.success(f"✅ {site}: Found {len(working_urls)} working URLs")
            else:
                logger.error(f"❌ {site}: No working URLs found")
        
        return results

    def get_enhanced_headers(self, site: str) -> Dict[str, str]:
        """Get enhanced headers specific to each site to avoid bot detection"""
        base_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate", 
            "Sec-Fetch-Site": "cross-site",
            "Sec-CH-UA": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            "Sec-CH-UA-Mobile": "?0",
            "Sec-CH-UA-Platform": '"Windows"'
        }
        
        # Site-specific header modifications
        if site == "moneycontrol":
            base_headers.update({
                "Referer": "https://www.moneycontrol.com/",
                "Cache-Control": "max-age=0"
            })
        elif site == "trendlyne":
            base_headers.update({
                "Referer": "https://trendlyne.com/",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            })
        elif site == "tickertape":
            base_headers.update({
                "Referer": "https://www.tickertape.in/",
                "Origin": "https://www.tickertape.in"
            })
        
        return base_headers

# Async function to run the URL pattern testing
async def main():
    """Test all URL patterns"""
    updater = SiteURLUpdater()
    results = await updater.update_all_patterns()
    
    logger.info("🎯 URL Pattern Testing Results:")
    for site, urls in results.items():
        logger.info(f"{site}: {len(urls)} working URLs")
        for url in urls:
            logger.info(f"  ✅ {url}")

if __name__ == "__main__":
    asyncio.run(main())
