#!/usr/bin/env python3
"""
Quick Screener Agent Price Verification
Tests immediate price extraction capability
"""
import asyncio
from backend.agents.stealth.screener_agent import ScreenerAgent

async def quick_price_test():
    """Quick test to verify price extraction works"""
    print("⚡ QUICK PRICE EXTRACTION TEST")
    print("=" * 40)
    
    agent = ScreenerAgent()
    
    # Test with TCS - usually reliable
    symbol = "TCS"
    print(f"📊 Testing {symbol} price extraction...")
    
    try:
        # Test the primary fetch method directly
        print("1️⃣ Testing primary source...")
        primary_result = await agent._fetch_primary_source(symbol)
        if primary_result and primary_result.get('success'):
            print(f"   ✅ Primary source: SUCCESS")
            data = primary_result.get('data', {})
            if isinstance(data, dict) and 'price' in data:
                print(f"   💰 Price found: ₹{data.get('price', 'N/A')}")
            else:
                print(f"   ⚠️ Data format: {type(data)} - {str(data)[:100]}...")
        else:
            print(f"   ❌ Primary source: FAILED - {primary_result}")
        
        # Test full execution
        print("\n2️⃣ Testing full execution...")
        result = await agent.execute(symbol)
        if result and result.get('error') is None:
            print(f"   ✅ Full execution: SUCCESS")
            print(f"   📊 Verdict: {result.get('verdict', 'N/A')}")
            print(f"   🎯 Confidence: {result.get('confidence', 0):.1%}")
            
            details = result.get('details', {})
            price_data = details.get('price_data', {})
            current_price = price_data.get('current_price')
            
            if current_price:
                print(f"   💰 Current Price: ₹{current_price}")
                print(f"   📈 Market Cap: {price_data.get('market_cap', 'N/A')}")
                print(f"   📊 PE Ratio: {price_data.get('pe_ratio', 'N/A')}")
            else:
                print(f"   ⚠️ No price data in result")
        else:
            print(f"   ❌ Full execution: FAILED - {result.get('error', 'Unknown')}")
            
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(quick_price_test())
