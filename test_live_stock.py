#!/usr/bin/env python3
"""
Test script to verify live stock data functionality
"""
import asyncio
import httpx
import json
from datetime import datetime

API_BASE = "http://localhost:8000"

async def test_live_stock_data():
    """Test live stock data endpoints"""
    print("🔍 Testing Zion Market Analysis Platform - Live Stock Data")
    print("=" * 60)
    
    # Test symbols (mix of US and Indian stocks)
    test_symbols = [
        "AAPL",      # Apple (US)
        "MSFT",      # Microsoft (US) 
        "GOOGL",     # Google (US)
        "RELIANCE",  # Reliance Industries (Indian)
        "TCS",       # Tata Consultancy Services (Indian)
        "INFY",      # Infosys (Indian)
        "NIFTY",     # Nifty 50 Index
    ]
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        print(f"📡 Testing API connectivity to {API_BASE}")
        
        # Test health endpoint
        try:
            response = await client.get(f"{API_BASE}/api/health")
            if response.status_code == 200:
                print("✅ API Health Check: PASSED")
                health_data = response.json()
                print(f"   Status: {health_data.get('status', 'Unknown')}")
            else:
                print(f"❌ API Health Check: FAILED ({response.status_code})")
                return
        except Exception as e:
            print(f"❌ API Health Check: FAILED - {e}")
            return
        
        print("\n📊 Testing Live Stock Data Analysis:")
        print("-" * 40)
        
        for symbol in test_symbols:
            try:
                print(f"\n🔍 Testing symbol: {symbol}")
                
                # Test symbol validation first
                validation_response = await client.get(f"{API_BASE}/api/symbols/validate/{symbol}")
                if validation_response.status_code == 200:
                    validation_data = validation_response.json()
                    print(f"   ✅ Symbol Validation: {validation_data.get('status', 'Valid')}")
                    if 'normalized_symbol' in validation_data:
                        print(f"   📝 Normalized: {validation_data['normalized_symbol']}")
                else:
                    print(f"   ⚠️  Symbol Validation: {validation_response.status_code}")
                
                # Test stock analysis
                analysis_response = await client.get(f"{API_BASE}/api/analyze/{symbol}")
                if analysis_response.status_code == 200:
                    analysis_data = analysis_response.json()
                    print(f"   ✅ Analysis: SUCCESS")
                    
                    # Extract key data points
                    if 'verdict' in analysis_data:
                        verdict = analysis_data['verdict']
                        print(f"   💡 Verdict: {verdict.get('overall_verdict', 'N/A')}")
                        print(f"   📈 Score: {verdict.get('overall_score', 'N/A')}")
                    
                    if 'market_data' in analysis_data:
                        market_data = analysis_data['market_data']
                        if isinstance(market_data, dict) and symbol in market_data:
                            symbol_data = market_data[symbol]
                            price = symbol_data.get('price', 'N/A')
                            source = symbol_data.get('source', 'N/A')
                            print(f"   💰 Current Price: {price} (Source: {source})")
                    
                elif analysis_response.status_code == 401:
                    print(f"   🔐 Analysis: Authentication required")
                    # Try without auth for testing
                    continue
                else:
                    print(f"   ❌ Analysis: FAILED ({analysis_response.status_code})")
                    if analysis_response.status_code < 500:
                        try:
                            error_data = analysis_response.json()
                            print(f"   📝 Error: {error_data.get('detail', 'Unknown error')}")
                        except:
                            pass
                
            except Exception as e:
                print(f"   ❌ Error testing {symbol}: {e}")
            
            # Small delay between requests to be respectful
            await asyncio.sleep(0.5)
        
        print("\n" + "=" * 60)
        print("🎯 Live Stock Data Test Complete!")
        print(f"⏰ Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    asyncio.run(test_live_stock_data())
