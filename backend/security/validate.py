from pydantic import BaseModel, Field, validator
from typing import Optional
from backend.utils.symbol_normalizer_fixed import validate_indian_symbol, IndianEquitySymbolNormalizer


class SymbolRequest(BaseModel):
    symbol: str = Field(..., pattern=r"^[A-Z0-9^.\-&]{1,20}$")  # Enhanced NSE/BSE compatible pattern
    
    @validator('symbol')
    def validate_indian_symbol_format(cls, v):
        """Enhanced validation for Indian equity symbols"""
        if not v:
            raise ValueError("Symbol cannot be empty")
            
        # Basic cleanup
        v = v.upper().strip()
        
        # Validate using our normalizer
        is_valid, error_msg = validate_indian_symbol(v)
        if not is_valid:
            raise ValueError(f"Invalid Indian equity symbol: {error_msg}")
            
        # Additional checks for known Indian symbols
        if not IndianEquitySymbolNormalizer.is_indian_symbol(v):
            # Log warning but don't reject - might be international symbol
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Symbol {v} doesn't appear to be an Indian equity symbol")
            
        return v


class EnhancedSymbolRequest(BaseModel):
    """Enhanced symbol request with provider-specific normalization"""
    symbol: str
    provider: str = "yahoo"  # Default provider
    exchange: Optional[str] = None  # Optional exchange specification
    
    @validator('symbol')
    def validate_and_normalize_symbol(cls, v):
        """Validate and normalize symbol"""
        if not v:
            raise ValueError("Symbol cannot be empty")
            
        v = v.upper().strip()
        
        # Validate format
        is_valid, error_msg = validate_indian_symbol(v)
        if not is_valid:
            raise ValueError(f"Invalid symbol format: {error_msg}")
            
        return v
    
    @property
    def normalized_symbol(self) -> str:
        """Get normalized symbol for the specified provider"""
        from backend.utils.symbol_normalizer_fixed import normalize_indian_symbol
        return normalize_indian_symbol(self.symbol, self.provider)
    
    @validator('provider')
    def validate_provider(cls, v):
        """Validate provider name"""
        valid_providers = [
            "yahoo", "yahoo_finance", "yfinance",
            "alpha_vantage", "alphavantage", 
            "polygon", "finnhub", "manual"
        ]
        if v.lower() not in valid_providers:
            raise ValueError(f"Invalid provider. Must be one of: {valid_providers}")
        return v.lower()
    
    @validator('exchange')
    def validate_exchange(cls, v):
        """Validate exchange if provided"""
        if v is None:
            return v
            
        valid_exchanges = ["NSE", "BSE", "INDEX"]
        if v.upper() not in valid_exchanges:
            raise ValueError(f"Invalid exchange. Must be one of: {valid_exchanges}")
        return v.upper()
