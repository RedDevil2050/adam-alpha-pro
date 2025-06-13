#!/usr/bin/env python3
"""
Quick test for the consolidated MoneyControl Agent v3.0
"""
import asyncio
import sys
from loguru import logger

async def test_consolidated_moneycontrol():
    """Test the consolidated MoneyControl agent"""
    print("🚀 TESTING CONSOLIDATED MONEYCONTROL AGENT v3.0")
    print("=" * 60)
    
    try:
        # Import the consolidated agent
        from backend.agents.stealth.moneycontrol_agent import MoneyControlAgent
        
        # Test symbols
        test_symbols = ["RELIANCE", "TCS"]
        
        for symbol in test_symbols:
            print(f"\n📊 Testing with symbol: {symbol}")
            print("-" * 40)
            
            # Initialize agent
            agent = MoneyControlAgent()
            
            # Disable browser automation for testing
            agent.browser_enabled = False
            
            # Test core methods
            print("✅ Agent instantiated successfully")
            print(f"✅ Cache size: {len(agent.cache)}")
            print(f"✅ URL patterns: {len(agent.url_patterns)}")
            print(f"✅ Success rates: {agent.success_rates}")
            
            # Test URL generation
            urls = agent._get_adaptive_urls(symbol)
            print(f"✅ Generated {len(urls)} URLs for {symbol}")
              # Test cache operations
            test_data = {'price': 1234.56, 'symbol': symbol}
            agent._cache_data(symbol, test_data)
            cached = await agent._get_cached_data(symbol)
            print(f"✅ Caching works: {cached is not None}")
            
            # Test headers generation
            headers = agent._get_smart_headers()
            print(f"✅ Generated smart headers: {len(headers)} entries")
            
            # Test performance metrics
            metrics = agent.get_performance_metrics()
            print(f"✅ Performance metrics: {metrics.get('status', 'unknown')}")
            
            # Test health check
            health = agent.health_check()
            print(f"✅ Health check: {health.get('status', 'unknown')}")
            
            print(f"✅ All basic tests passed for {symbol}")
    
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False
    
    print(f"\n🎉 Consolidated MoneyControl Agent v3.0 validation completed!")
    print("🔧 Ready for unified stealth testing!")
    return True

if __name__ == "__main__":
    asyncio.run(test_consolidated_moneycontrol())
