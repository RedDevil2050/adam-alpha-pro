#!/usr/bin/env python3
"""
Test suite for Indian equity symbol handling functionality.
This replaces all the scattered test scripts in the root directory.
"""

import sys
import os
import pytest
import asyncio
from unittest.mock import patch, MagicMock

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

@pytest.fixture
def sample_symbols():
    """Sample Indian equity symbols for testing."""
    return {
        'basic': ['RELIANCE', 'TCS', 'INFY', 'HDFC'],
        'with_exchange': ['NSE:RELIANCE', 'BSE:TCS'],
        'with_suffix': ['RELIANCE.NS', 'TCS.BO'],
        'indices': ['^NSEI', '^BSESN'],
        'invalid': ['', 'INVALID@#', 'THISISINVALIDTOOLONG', '1']
    }

class TestSymbolNormalizer:
    """Test the IndianEquitySymbolNormalizer class."""
    
    def test_import_normalizer(self):
        """Test that the symbol normalizer can be imported."""
        from backend.utils.symbol_normalizer_fixed import IndianEquitySymbolNormalizer
        normalizer = IndianEquitySymbolNormalizer()
        assert normalizer is not None
    
    def test_validate_symbols(self, sample_symbols):
        """Test symbol validation."""
        from backend.utils.symbol_normalizer_fixed import IndianEquitySymbolNormalizer
        normalizer = IndianEquitySymbolNormalizer()
        
        # Valid symbols should pass
        for symbol in sample_symbols['basic']:
            assert normalizer.is_indian_symbol(symbol)
        
        # Invalid symbols should fail
        for symbol in sample_symbols['invalid']:
            assert not normalizer.is_indian_symbol(symbol)
    
    def test_normalize_for_yahoo(self, sample_symbols):
        """Test normalization for Yahoo Finance provider."""
        from backend.utils.symbol_normalizer_fixed import IndianEquitySymbolNormalizer
        normalizer = IndianEquitySymbolNormalizer()
        
        assert normalizer.get_provider_symbol('RELIANCE', 'yahoo') == 'RELIANCE.NS'
        assert normalizer.get_provider_symbol('TCS.BO', 'yahoo') == 'TCS.BO'
        assert normalizer.normalize_for_yahoo_finance('INFY') == 'INFY.NS'
    
    def test_normalize_for_alpha_vantage(self):
        """Test normalization for Alpha Vantage provider."""
        from backend.utils.symbol_normalizer_fixed import IndianEquitySymbolNormalizer
        normalizer = IndianEquitySymbolNormalizer()
        
        assert normalizer.get_provider_symbol('RELIANCE', 'alpha_vantage') == 'RELIANCE'
        assert normalizer.normalize_for_alpha_vantage('TCS.NS') == 'TCS'

class TestValidationIntegration:
    """Test integration with the validation system."""
    
    def test_symbol_request_validation(self):
        """Test that SymbolRequest validates Indian equity symbols."""
        from backend.security.validate import SymbolRequest
        
        # Valid symbol should work
        request = SymbolRequest(symbol='RELIANCE')
        assert request.symbol == 'RELIANCE'
        
        # Invalid symbol should raise validation error
        with pytest.raises(Exception):
            SymbolRequest(symbol='INVALID@#')
    
    def test_enhanced_symbol_request(self):
        """Test EnhancedSymbolRequest with normalized_symbol property."""
        from backend.security.validate import EnhancedSymbolRequest
        
        request = EnhancedSymbolRequest(symbol='RELIANCE', provider='yahoo')
        assert request.normalized_symbol == 'RELIANCE.NS'
        
        request = EnhancedSymbolRequest(symbol='TCS', provider='alpha_vantage')
        assert request.normalized_symbol == 'TCS'

class TestDataProviderIntegration:
    """Test integration with data providers."""
    
    @pytest.mark.asyncio
    async def test_unified_provider_normalization(self):
        """Test that UnifiedDataProvider normalizes symbols."""
        from backend.data.providers.unified_provider import UnifiedDataProvider
        
        provider = UnifiedDataProvider()
        
        # Test the internal normalization method
        normalized = provider._normalize_symbol_for_provider('RELIANCE', 'yahoo')
        assert normalized == 'RELIANCE.NS'
    
    def test_yahoo_provider_normalization(self):
        """Test Yahoo Finance provider uses normalization."""
        from backend.data.providers.yahoo_finance_provider import YahooFinanceProvider
        
        provider = YahooFinanceProvider()
        # Test that the provider exists and can be instantiated
        assert provider is not None

@pytest.mark.integration
class TestEndToEndFlow:
    """Test the complete flow from symbol input to data retrieval."""
    
    @pytest.mark.asyncio
    async def test_price_data_fetch_flow(self):
        """Test complete flow of fetching price data with symbol normalization."""
        from backend.data.providers.unified_provider import UnifiedDataProvider
        from backend.security.validate import EnhancedSymbolRequest
        
        # Create request with Indian symbol
        request = EnhancedSymbolRequest(symbol='RELIANCE', provider='yahoo')
        
        # Verify normalization works
        assert request.normalized_symbol == 'RELIANCE.NS'
        
        # Test with provider (mock the actual API call)
        provider = UnifiedDataProvider()
        
        with patch.object(provider, '_fetch_from_provider') as mock_fetch:
            mock_fetch.return_value = {'price': 2500.0, 'volume': 1000000}
            
            # This should use the normalized symbol internally
            result = await provider.fetch_data_resilient(request.normalized_symbol, 'price')
            
            # Verify we got some result
            assert result is not None

def test_system_components_available():
    """Test that all system components are available and importable."""
    components = [
        'backend.utils.symbol_normalizer',
        'backend.security.validate', 
        'backend.data.providers.unified_provider',
        'backend.data.providers.yahoo_finance_provider',
        'backend.data.providers.alpha_vantage_provider'
    ]
    
    for component in components:
        try:
            __import__(component)
        except ImportError as e:
            pytest.fail(f"Failed to import {component}: {e}")

def test_convenience_functions():
    """Test the convenience functions work properly."""
    from backend.utils.symbol_normalizer_fixed import normalize_indian_symbol, validate_indian_symbol
    
    # Test normalization
    assert normalize_indian_symbol('RELIANCE', 'yahoo') == 'RELIANCE.NS'
    assert normalize_indian_symbol('TCS', 'alpha_vantage') == 'TCS'
    
    # Test validation
    is_valid, error = validate_indian_symbol('RELIANCE')
    assert is_valid == True
    assert error == ""
    
    is_valid, error = validate_indian_symbol('INVALID@#')
    assert is_valid == False
    assert error != ""

if __name__ == '__main__':
    """Run tests directly if script is executed."""
    print("Running Indian Equity Symbol System Tests...")
    pytest.main([__file__, '-v', '--tb=short'])
