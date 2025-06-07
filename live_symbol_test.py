#!/usr/bin/env python3
"""
Live testing script for Indian equity symbol system.
Tests real symbol normalization and data fetching with actual market symbols.
"""

import sys
import os
import asyncio
import time
from datetime import datetime
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

def test_live_symbols():
    """Test the system with a variety of live Indian equity symbols."""
    
    print("🔴 LIVE INDIAN EQUITY SYMBOL TESTING")
    print("=" * 60)
    print(f"🕐 Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Diverse set of real Indian equity symbols
    test_symbols = [
        # Major stocks - different formats
        'RELIANCE',        # Raw NSE symbol
        'TCS.NS',          # Already formatted for Yahoo
        'INFY.BO',         # BSE format
        'HDFCBANK',        # Raw NSE symbol
        'ICICIBANK.NS',    # Already formatted
        
        # Mid-cap stocks
        'BAJFINANCE',      # Raw symbol
        'DMART',           # Raw symbol
        'TITAN.NS',        # Formatted
        
        # Indices
        '^NSEI',           # Nifty 50
        '^BSESN',          # Sensex
        'NIFTY',           # Index by name
        'SENSEX',          # Index by name
        
        # Some challenging cases
        'M&M',             # Symbol with &
        'L&T',             # Another symbol with &
        'ITC',             # Short symbol
        
        # BSE numerical codes
        '500325',          # Reliance BSE code
        '532540',          # TCS BSE code
        
        # Invalid symbols (should be handled gracefully)
        '',                # Empty
        'INVALID@#',       # Invalid characters
        'TOOLONGSYMBOLNAME', # Too long
        'USTECH',          # Might be international
    ]
    
    print("📋 Testing Symbol Normalization...")
    print("-" * 40)
    
    success_count = 0
    total_tests = len(test_symbols)
    
    try:
        from backend.utils.symbol_normalizer import (
            IndianEquitySymbolNormalizer, 
            normalize_indian_symbol, 
            validate_indian_symbol
        )
        
        normalizer = IndianEquitySymbolNormalizer()
        
        for i, symbol in enumerate(test_symbols, 1):
            print(f"{i:2d}. Testing: '{symbol}'")
            
            try:
                # Test validation
                is_valid, error_msg = validate_indian_symbol(symbol)
                
                # Test Indian symbol detection
                is_indian = normalizer.is_indian_symbol(symbol)
                
                # Test normalization for different providers
                yahoo_format = normalize_indian_symbol(symbol, 'yahoo')
                av_format = normalize_indian_symbol(symbol, 'alpha_vantage')
                
                # Test exchange detection
                exchange = normalizer.detect_exchange(symbol)
                
                print(f"    ✓ Valid: {is_valid}")
                if not is_valid:
                    print(f"    ✗ Error: {error_msg}")
                print(f"    ✓ Indian: {is_indian}")
                print(f"    ✓ Exchange: {exchange}")
                print(f"    ✓ Yahoo: '{yahoo_format}'")
                print(f"    ✓ AlphaVantage: '{av_format}'")
                
                success_count += 1
                
            except Exception as e:
                print(f"    ❌ Error processing '{symbol}': {e}")
            
            print()
    
    except Exception as e:
        print(f"❌ Failed to import normalizer: {e}")
        return
    
    print("📊 Testing Enhanced Validation...")
    print("-" * 40)
    
    try:
        from backend.security.validate import EnhancedSymbolRequest
        
        # Test with valid symbols
        valid_symbols = ['RELIANCE', 'TCS', 'INFY', '^NSEI']
        
        for symbol in valid_symbols:
            try:
                request = EnhancedSymbolRequest(symbol=symbol, provider='yahoo')
                print(f"✓ {symbol:10} -> {request.normalized_symbol}")
            except Exception as e:
                print(f"❌ {symbol:10} -> Error: {e}")
        
    except Exception as e:
        print(f"❌ Enhanced validation test failed: {e}")
    
    print()
    print("🔗 Testing Data Provider Integration...")
    print("-" * 40)
    
    try:
        from backend.data.providers.unified_provider import UnifiedDataProvider
        
        provider = UnifiedDataProvider()
        
        # Test normalization within provider
        test_provider_symbols = ['RELIANCE', 'TCS.NS', '^NSEI']
        
        for symbol in test_provider_symbols:
            try:
                if hasattr(provider, '_normalize_symbol_for_provider'):
                    normalized = provider._normalize_symbol_for_provider(symbol, 'yahoo')
                    print(f"✓ Provider normalization: {symbol:10} -> {normalized}")
                else:
                    print("⚠️  Provider doesn't have _normalize_symbol_for_provider method")
                    break
            except Exception as e:
                print(f"❌ Provider test failed for {symbol}: {e}")
        
    except Exception as e:
        print(f"❌ Data provider integration test failed: {e}")
    
    print()
    print("=" * 60)
    print(f"📈 RESULTS: {success_count}/{total_tests} symbols processed successfully")
    
    if success_count >= total_tests * 0.8:  # 80% success rate
        print("🎉 System performing well with live symbols!")
    elif success_count >= total_tests * 0.6:  # 60% success rate
        print("⚠️  System working but has some issues to address")
    else:
        print("❌ System needs significant improvements")
    
    print()
    print("🔍 AREAS FOR IMPROVEMENT:")
    print("1. Check error handling for edge cases")
    print("2. Verify symbol detection accuracy")
    print("3. Test with more exotic Indian symbols")
    print("4. Performance optimization for large symbol lists")
    print("5. Add more BSE numerical codes to test database")
    
    return success_count, total_tests

async def test_live_data_fetching():
    """Test actual data fetching with normalized symbols."""
    
    print("\n💹 LIVE DATA FETCHING TEST")
    print("=" * 60)
    
    # Select a few reliable symbols for data fetching
    test_symbols = ['RELIANCE', 'TCS', 'INFY', '^NSEI']
    
    try:
        from backend.data.providers.unified_provider import UnifiedDataProvider
        from backend.utils.symbol_normalizer import normalize_indian_symbol
        
        provider = UnifiedDataProvider()
        
        for symbol in test_symbols:
            print(f"\n📊 Testing data fetch for: {symbol}")
            
            try:
                # Normalize symbol for Yahoo Finance
                normalized = normalize_indian_symbol(symbol, 'yahoo')
                print(f"   Normalized: {normalized}")
                
                # Try to fetch data (with timeout)
                start_time = time.time()
                
                # Check what methods are available
                available_methods = [method for method in dir(provider) 
                                   if method.startswith('fetch') and not method.startswith('_')]
                
                print(f"   Available fetch methods: {available_methods}")
                
                # Try the main data fetching method
                if hasattr(provider, 'fetch_data_resilient'):
                    try:
                        data = await asyncio.wait_for(
                            provider.fetch_data_resilient(normalized, 'price'),
                            timeout=10.0
                        )
                        
                        fetch_time = time.time() - start_time
                        print(f"   ✅ Data fetched in {fetch_time:.2f}s")
                        
                        if data:
                            print(f"   📈 Data keys: {list(data.keys())}")
                            if 'price' in data:
                                print(f"   💰 Price: {data['price']}")
                        else:
                            print("   ⚠️  No data returned")
                            
                    except asyncio.TimeoutError:
                        print("   ⏰ Data fetch timed out (>10s)")
                    except Exception as e:
                        print(f"   ❌ Data fetch error: {e}")
                else:
                    print("   ⚠️  fetch_data_resilient method not found")
                
            except Exception as e:
                print(f"   ❌ Error processing {symbol}: {e}")
    
    except Exception as e:
        print(f"❌ Live data fetching test failed: {e}")

def identify_improvement_areas(success_count: int, total_tests: int):
    """Analyze results and suggest improvements."""
    
    print("\n🔧 IMPROVEMENT ANALYSIS")
    print("=" * 60)
    
    success_rate = (success_count / total_tests) * 100 if total_tests > 0 else 0
    
    print(f"📊 Overall Success Rate: {success_rate:.1f}%")
    print()
    
    if success_rate >= 90:
        print("🌟 EXCELLENT PERFORMANCE!")
        print("Suggested optimizations:")
        print("• Add more Indian stocks to MAJOR_STOCKS database")
        print("• Implement caching for frequently used symbols")
        print("• Add performance monitoring")
        
    elif success_rate >= 75:
        print("✅ GOOD PERFORMANCE!")
        print("Areas for improvement:")
        print("• Review failed symbol patterns")
        print("• Enhance validation for edge cases")
        print("• Add more comprehensive symbol database")
        
    elif success_rate >= 50:
        print("⚠️  MODERATE PERFORMANCE")
        print("Critical improvements needed:")
        print("• Fix symbol detection logic")
        print("• Improve error handling")
        print("• Add more robust validation")
        
    else:
        print("❌ POOR PERFORMANCE")
        print("Major overhaul needed:")
        print("• Review core normalization logic")
        print("• Fix validation framework")
        print("• Add comprehensive error handling")
    
    print()
    print("🚀 RECOMMENDED NEXT STEPS:")
    print("1. Add more stocks to MAJOR_STOCKS set")
    print("2. Implement symbol caching mechanism")
    print("3. Add performance metrics collection")
    print("4. Create comprehensive test database of Indian symbols")
    print("5. Add monitoring and alerting for failed normalizations")

def main():
    """Run the complete live testing suite."""
    
    print("🚀 ZION INDIAN EQUITY SYSTEM - LIVE TESTING")
    print("=" * 80)
    print()
    
    # Test 1: Symbol normalization
    success_count, total_tests = test_live_symbols()
    
    # Test 2: Live data fetching
    print("\n" + "=" * 80)
    asyncio.run(test_live_data_fetching())
    
    # Test 3: Performance analysis
    print("\n" + "=" * 80)
    identify_improvement_areas(success_count, total_tests)
    
    print("\n" + "=" * 80)
    print(f"🏁 LIVE TESTING COMPLETE - {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 80)

if __name__ == '__main__':
    main()
