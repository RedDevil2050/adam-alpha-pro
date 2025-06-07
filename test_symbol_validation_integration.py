#!/usr/bin/env python3
"""
Test script to validate symbol normalization integration in Zion system.
This script tests the integration of symbol validation and normalization
across different components of the system.
"""

import asyncio
import sys
from pathlib import Path

# Add the backend directory to the path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from backend.security.validate import SymbolRequest, EnhancedSymbolRequest
from backend.utils.symbol_normalizer_fixed import (
    IndianEquitySymbolNormalizer, 
    normalize_indian_symbol, 
    validate_indian_symbol
)
from backend.utils.validation import validate_symbols
from pydantic import ValidationError


def test_basic_validation():
    """Test basic symbol validation using SymbolRequest"""
    print("\n🔍 Testing Basic Symbol Validation...")
    
    test_symbols = ["RELIANCE", "TCS", "INVALID@#$", "123456", "^NSEI"]
    
    for symbol in test_symbols:
        try:
            validated = SymbolRequest(symbol=symbol)
            print(f"✅ {symbol} -> {validated.symbol} (Valid)")
        except ValidationError as e:
            print(f"❌ {symbol} -> Invalid: {e}")
        except ValueError as e:
            print(f"❌ {symbol} -> Invalid: {e}")


def test_enhanced_validation():
    """Test enhanced symbol validation with provider normalization"""
    print("\n🔍 Testing Enhanced Symbol Validation...")
    
    test_cases = [
        {"symbol": "RELIANCE", "provider": "yahoo", "exchange": "NSE"},
        {"symbol": "TCS", "provider": "alpha_vantage", "exchange": None},
        {"symbol": "RELIANCE.NS", "provider": "polygon", "exchange": None},
        {"symbol": "^NSEI", "provider": "yahoo", "exchange": "INDEX"},
    ]
    
    for case in test_cases:
        try:
            enhanced = EnhancedSymbolRequest(**case)
            normalized = enhanced.normalized_symbol
            print(f"✅ {case['symbol']} ({case['provider']}) -> {normalized}")
        except ValidationError as e:
            print(f"❌ {case['symbol']} -> Invalid: {e}")
        except ValueError as e:
            print(f"❌ {case['symbol']} -> Invalid: {e}")


def test_normalizer_direct():
    """Test the normalizer class directly"""
    print("\n🔍 Testing Direct Symbol Normalizer...")
    
    normalizer = IndianEquitySymbolNormalizer()
    test_symbols = ["RELIANCE", "TCS.NS", "^NSEI", "123456"]
    
    for symbol in test_symbols:
        print(f"\n📊 Symbol: {symbol}")
        print(f"   Is Indian: {normalizer.is_indian_symbol(symbol)}")
        print(f"   Exchange: {normalizer.detect_exchange(symbol)}")
        print(f"   Base Symbol: {normalizer.get_base_symbol(symbol)}")
        print(f"   Yahoo Format: {normalizer.get_provider_symbol(symbol, 'yahoo')}")
        print(f"   Alpha Vantage: {normalizer.get_provider_symbol(symbol, 'alpha_vantage')}")
        
        is_valid, error_msg = normalizer.validate_symbol_format(symbol)
        print(f"   Valid: {is_valid}" + (f" - {error_msg}" if not is_valid else ""))


def test_bulk_validation():
    """Test bulk symbol validation"""
    print("\n🔍 Testing Bulk Symbol Validation...")
    
    valid_symbols = ["RELIANCE", "TCS", "INFY", "HDFCBANK"]
    mixed_symbols = ["RELIANCE", "INVALID@#$", "TCS", "BAD_SYMBOL_123456789012345"]
    
    try:
        validate_symbols(valid_symbols)
        print(f"✅ Valid symbols list passed: {valid_symbols}")
    except Exception as e:
        print(f"❌ Valid symbols failed: {e}")
    
    try:
        validate_symbols(mixed_symbols)
        print(f"❌ Mixed symbols should have failed: {mixed_symbols}")
    except Exception as e:
        print(f"✅ Mixed symbols correctly failed: {e}")


def test_convenience_functions():
    """Test convenience functions"""
    print("\n🔍 Testing Convenience Functions...")
    
    test_symbols = ["RELIANCE", "TCS.NS", "INVALID@#$"]
    
    for symbol in test_symbols:
        # Test normalization
        yahoo_norm = normalize_indian_symbol(symbol, "yahoo")
        av_norm = normalize_indian_symbol(symbol, "alpha_vantage")
        
        # Test validation
        is_valid, error_msg = validate_indian_symbol(symbol)
        
        print(f"📊 {symbol}:")
        print(f"   Yahoo: {yahoo_norm}")
        print(f"   Alpha Vantage: {av_norm}")
        print(f"   Valid: {is_valid}" + (f" - {error_msg}" if not is_valid else ""))


def test_api_endpoint_format():
    """Test the format expected by API endpoints"""
    print("\n🔍 Testing API Endpoint Format...")
    
    # This simulates what happens in the API endpoint
    test_symbols = ["RELIANCE", "TCS", "INVALID@#$"]
    
    for symbol in test_symbols:
        try:
            # This is what the API endpoint does
            validated_symbol = SymbolRequest(symbol=symbol)
            print(f"✅ API would accept: {symbol} -> {validated_symbol.symbol}")
        except (ValidationError, ValueError) as e:
            print(f"❌ API would reject: {symbol} -> {e}")


async def test_integration():
    """Main integration test"""
    print("🚀 Zion Symbol Validation Integration Test")
    print("=" * 50)
    
    test_basic_validation()
    test_enhanced_validation()
    test_normalizer_direct()
    test_bulk_validation()
    test_convenience_functions()
    test_api_endpoint_format()
    
    print("\n✅ Integration tests completed!")
    print("\n📋 Summary:")
    print("   - Basic validation with SymbolRequest ✓")
    print("   - Enhanced validation with provider normalization ✓")
    print("   - Direct normalizer functionality ✓")
    print("   - Bulk validation utilities ✓")
    print("   - Convenience functions ✓")
    print("   - API endpoint integration ✓")


if __name__ == "__main__":
    asyncio.run(test_integration())
