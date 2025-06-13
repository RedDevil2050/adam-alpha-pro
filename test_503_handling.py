#!/usr/bin/env python3
"""
Test script for handling 503 Service Unavailable errors from financial data sources.
This script tests and improves resilience when web scraping financial data.
"""

import asyncio
import httpx
import time
from typing import Dict, List, Optional
from loguru import logger

class ServiceUnavailableHandler:
    """Enhanced handler for 503 Service Unavailable errors."""
    
    def __init__(self):
        self.max_retries = 3
        self.base_delay = 2  # seconds
        self.max_delay = 30  # seconds
        self.backoff_multiplier = 2
        
    async def handle_503_with_backoff(self, url: str, headers: Dict) -> Optional[httpx.Response]:
        """Handle 503 errors with exponential backoff."""
        
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(
                    timeout=20, 
                    follow_redirects=True,
                    headers=headers
                ) as client:
                    logger.info(f"Attempt {attempt + 1}/{self.max_retries} for URL: {url}")
                    response = await client.get(url)
                    
                    if response.status_code == 200:
                        logger.success(f"✅ Success on attempt {attempt + 1}")
                        return response
                        
                    elif response.status_code == 503:
                        delay = min(self.base_delay * (self.backoff_multiplier ** attempt), self.max_delay)
                        logger.warning(f"🔴 503 Service Unavailable - waiting {delay}s before retry {attempt + 1}")
                        
                        if attempt < self.max_retries - 1:  # Don't sleep on last attempt
                            await asyncio.sleep(delay)
                        continue
                        
                    else:
                        logger.warning(f"⚠️ Unexpected status code: {response.status_code}")
                        return response
                        
            except httpx.TimeoutException:
                logger.warning(f"⏱️ Timeout on attempt {attempt + 1}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.base_delay)
                continue
                
            except Exception as e:
                logger.error(f"❌ Error on attempt {attempt + 1}: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.base_delay)
                continue
        
        logger.error(f"❌ All {self.max_retries} attempts failed for {url}")
        return None

    def get_enhanced_headers(self) -> Dict[str, str]:
        """Get enhanced headers to reduce bot detection."""
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "DNT": "1",  # Do Not Track
            "Sec-GPC": "1",  # Global Privacy Control
        }

async def test_moneycontrol_503_handling():
    """Test MoneyControl with 503 error handling."""
    
    logger.info("🧪 Testing MoneyControl 503 Error Handling")
    
    handler = ServiceUnavailableHandler()
    headers = handler.get_enhanced_headers()
    
    # Test URLs that might return 503
    test_urls = [
        "https://www.moneycontrol.com/stock-price/RELIANCE",
        "https://www.moneycontrol.com/india/stockpricequote/RELIANCE",
        "https://www.moneycontrol.com/search/all?search=RELIANCE"
    ]
    
    results = []
    
    for url in test_urls:
        logger.info(f"🔍 Testing URL: {url}")
        start_time = time.time()
        
        response = await handler.handle_503_with_backoff(url, headers)
        
        elapsed_time = time.time() - start_time
        
        if response:
            result = {
                "url": url,
                "status_code": response.status_code,
                "content_length": len(response.text) if response.text else 0,
                "elapsed_time": round(elapsed_time, 2),
                "success": response.status_code == 200
            }
        else:
            result = {
                "url": url,
                "status_code": None,
                "content_length": 0,
                "elapsed_time": round(elapsed_time, 2),
                "success": False
            }
        
        results.append(result)
        logger.info(f"Result: {result}")
        
        # Add delay between requests to be respectful
        await asyncio.sleep(3)
    
    # Summary
    logger.info("\n📊 Test Results Summary:")
    successful_requests = sum(1 for r in results if r["success"])
    logger.info(f"✅ Successful requests: {successful_requests}/{len(results)}")
    
    for result in results:
        status_emoji = "✅" if result["success"] else "❌"
        logger.info(f"{status_emoji} {result['url']} - Status: {result['status_code']} - Time: {result['elapsed_time']}s")
    
    return results

async def test_alternative_strategies():
    """Test alternative strategies when 503 errors persist."""
    
    logger.info("🔄 Testing Alternative Strategies for 503 Errors")
    
    strategies = [
        {
            "name": "Different User Agent",
            "headers": {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }
        },
        {
            "name": "Mobile User Agent",
            "headers": {
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15"
            }
        },
        {
            "name": "Minimal Headers",
            "headers": {
                "User-Agent": "Python/httpx"
            }
        }
    ]
    
    test_url = "https://www.moneycontrol.com/stock-price/RELIANCE"
    
    for strategy in strategies:
        logger.info(f"🔍 Testing Strategy: {strategy['name']}")
        
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(test_url, headers=strategy["headers"])
                logger.info(f"Status: {response.status_code} - Content Length: {len(response.text)}")
                
                if response.status_code == 200:
                    logger.success(f"✅ {strategy['name']} worked!")
                elif response.status_code == 503:
                    logger.warning(f"🔴 {strategy['name']} got 503")
                else:
                    logger.info(f"⚠️ {strategy['name']} got {response.status_code}")
                    
        except Exception as e:
            logger.error(f"❌ {strategy['name']} error: {e}")
        
        await asyncio.sleep(2)  # Respectful delay

def main():
    """Main test function."""
    logger.info("🚀 Starting 503 Error Handling Tests")
    
    async def run_tests():
        # Test 503 handling
        await test_moneycontrol_503_handling()
        
        # Test alternative strategies
        await test_alternative_strategies()
        
        logger.info("✅ All tests completed!")
    
    asyncio.run(run_tests())

if __name__ == "__main__":
    main()
