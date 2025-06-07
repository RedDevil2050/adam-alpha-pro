"""
Symbol normalization utilities for Indian equity market symbols.
Handles conversion between different formats required by various data providers.
"""

import re
from typing import Optional, Tuple, Dict, Any
from loguru import logger


class IndianEquitySymbolNormalizer:
    """
    Normalizes Indian equity symbols for different data providers and exchanges.
    
    Supported formats:
    - Raw symbol: "RELIANCE", "TCS", "HDFCBANK"
    - Yahoo Finance: "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS" 
    - BSE format: "RELIANCE.BO", "TCS.BO", "HDFCBANK.BO"
    - Numerical symbols: "500325" (BSE codes)
    - Index symbols: "^NSEI", "^BSESN", "^INDIAVIX"
    """
    
    # Common Indian market indices
    INDIAN_INDICES = {
        "NIFTY": "^NSEI",
        "NIFTY50": "^NSEI", 
        "SENSEX": "^BSESN",
        "BANKNIFTY": "^NSEBANK",
        "INDIAVIX": "^INDIAVIX",
        "NSEI": "^NSEI",
        "BSESN": "^BSESN"
    }
    
    # Common Indian equity symbols (major stocks) - expanded list
    MAJOR_STOCKS = {
        "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", 
        "HINDUNILVR", "SBIN", "LT", "ITC", "KOTAKBANK",
        "BHARTIARTL", "ASIANPAINT", "HCLTECH", "AXISBANK", 
        "MARUTI", "BAJFINANCE", "DMART", "TITAN", "TECHM",
        "ULTRACEMCO", "NESTLEIND", "WIPRO", "ONGC", "NTPC",
        "BAJAJFINSV", "POWERGRID", "SUNPHARMA", "DRREDDY", "DIVISLAB",
        "BRITANNIA", "HEROMOTOCO", "BPCL", "EICHERMOT", "TATAMOTORS",
        "COALINDIA", "SHREECEM", "GRASIM", "JSWSTEEL", "TATASTEEL",
        "HINDALCO", "ADANIPORTS", "INDUSINDBK", "UPL", "CIPLA"
    }
    
    # BSE to NSE symbol mapping for major stocks
    BSE_TO_NSE_MAPPING = {
        "500325": "RELIANCE",
        "532540": "TCS", 
        "500180": "HDFCBANK",
        "500209": "INFY",
        "532174": "ICICIBANK",
        "500696": "HINDUNILVR",
        "500112": "SBIN",
        "500510": "LT",
        "500875": "ITC",
        "532281": "HCLTECH",
        "532215": "AXISBANK",
        "532500": "MARUTI",
        "500034": "BAJFINANCE",
        "543320": "DMART",
        "500114": "TITAN",
        "532755": "TECHM",
        "532538": "ULTRACEMCO",
        "500790": "NESTLEIND",
        "507685": "WIPRO",
        "500312": "ONGC",
        "532555": "NTPC"
    }
    
    # Exchange suffixes for different providers
    EXCHANGE_SUFFIXES = {
        "yahoo": {
            "NSE": ".NS",
            "BSE": ".BO"
        },
        "alpha_vantage": {
            "NSE": "",  # No suffix for AV
            "BSE": ""
        },
        "polygon": {
            "NSE": "",
            "BSE": ""
        }
    }
    
    @staticmethod
    def is_indian_symbol(symbol: str) -> bool:
        """
        Check if a symbol appears to be an Indian equity symbol.
        
        Args:
            symbol: The symbol to check
            
        Returns:
            bool: True if it appears to be an Indian symbol
        """
        if not symbol:
            return False
            
        symbol = symbol.upper().strip()
        
        # Check for common Indian indices
        if symbol.startswith("^") and any(idx in symbol for idx in ["NSEI", "BSESN", "INDIA"]):
            return True
            
        # Check for .NS or .BO suffix (Yahoo Finance format)
        if symbol.endswith((".NS", ".BO")):
            return True
            
        # Check for major Indian stocks
        base_symbol = symbol.replace(".NS", "").replace(".BO", "")
        if base_symbol in IndianEquitySymbolNormalizer.MAJOR_STOCKS:
            return True
            
        # Check for BSE numerical codes (typically 6 digits)
        if symbol.isdigit() and len(symbol) == 6:
            return True
            
        # Check BSE code mapping
        if symbol in IndianEquitySymbolNormalizer.BSE_TO_NSE_MAPPING:
            return True
            
        # Check for typical Indian stock symbol patterns
        # Indian symbols are typically 2-10 characters, alphanumeric with some special chars
        # Exclude short numeric-only strings that aren't BSE codes
        if (re.match(r'^[A-Z0-9&-]{2,10}$', symbol) and 
            not (symbol.isdigit() and len(symbol) < 6)):
            return True
            
        return False
    
    @staticmethod
    def normalize_for_yahoo_finance(symbol: str) -> str:
        """
        Normalize symbol for Yahoo Finance (adds .NS suffix for Indian equities).
        
        Args:
            symbol: Raw symbol to normalize
            
        Returns:
            str: Symbol formatted for Yahoo Finance
        """
        if not symbol:
            return symbol
            
        symbol = symbol.upper().strip()
        
        # Handle indices - they don't need .NS suffix
        if symbol.startswith("^"):
            return symbol
            
        # Check if it's a known index by name
        if symbol in IndianEquitySymbolNormalizer.INDIAN_INDICES:
            return IndianEquitySymbolNormalizer.INDIAN_INDICES[symbol]
            
        # If already has .NS or .BO suffix, return as is
        if symbol.endswith((".NS", ".BO")):
            return symbol
            
        # For BSE numerical codes, convert to NSE symbol or add .BO
        if symbol.isdigit() and len(symbol) == 6:
            # Try to map BSE code to NSE symbol first
            if symbol in IndianEquitySymbolNormalizer.BSE_TO_NSE_MAPPING:
                nse_symbol = IndianEquitySymbolNormalizer.BSE_TO_NSE_MAPPING[symbol]
                return f"{nse_symbol}.NS"
            else:
                # Use .BO for unmapped BSE codes
                return f"{symbol}.BO"
            
        # For regular equity symbols, add .NS (NSE default)
        if IndianEquitySymbolNormalizer.is_indian_symbol(symbol):
            return f"{symbol}.NS"
            
        # If not identified as Indian, return as is (might be international)
        return symbol
    
    @staticmethod
    def normalize_for_alpha_vantage(symbol: str) -> str:
        """
        Normalize symbol for Alpha Vantage (removes .NS/.BO suffixes).
        
        Args:
            symbol: Symbol to normalize
            
        Returns:
            str: Symbol formatted for Alpha Vantage
        """
        if not symbol:
            return symbol
            
        symbol = symbol.upper().strip()
        
        # Alpha Vantage typically uses raw symbols without exchange suffixes
        # Remove .NS and .BO suffixes
        if symbol.endswith((".NS", ".BO")):
            return symbol[:-3]
            
        # Handle indices
        if symbol.startswith("^"):
            # Alpha Vantage might use different format for indices
            index_map = {
                "^NSEI": "NSE:NIFTY",
                "^BSESN": "BSE:SENSEX", 
                "^INDIAVIX": "NSE:INDIAVIX",
                "^NSEBANK": "NSE:BANKNIFTY"
            }
            return index_map.get(symbol, symbol.replace("^", ""))
            
        return symbol
    
    @staticmethod
    def get_base_symbol(symbol: str) -> str:
        """
        Get the base symbol without exchange suffixes.
        
        Args:
            symbol: Symbol with or without suffixes
            
        Returns:
            str: Base symbol without suffixes
        """
        if not symbol:
            return symbol
            
        symbol = symbol.upper().strip()
        
        # Remove common suffixes
        if symbol.endswith((".NS", ".BO")):
            return symbol[:-3]
            
        # Handle indices
        if symbol.startswith("^"):
            return symbol
            
        return symbol
    
    @staticmethod
    def detect_exchange(symbol: str) -> str:
        """
        Detect the likely exchange for a symbol.
        
        Args:
            symbol: Symbol to analyze
            
        Returns:
            str: Detected exchange ('NSE', 'BSE', 'INDEX', 'UNKNOWN')
        """
        if not symbol:
            return "UNKNOWN"
            
        symbol = symbol.upper().strip()
        
        # Check for explicit exchange suffixes
        if symbol.endswith(".NS"):
            return "NSE"
        elif symbol.endswith(".BO"):
            return "BSE"
            
        # Check for indices
        if symbol.startswith("^") or symbol in IndianEquitySymbolNormalizer.INDIAN_INDICES:
            return "INDEX"
            
        # Check for BSE numerical codes
        if symbol.isdigit() and len(symbol) == 6:
            return "BSE"
            
        # Default to NSE for Indian symbols
        if IndianEquitySymbolNormalizer.is_indian_symbol(symbol):
            return "NSE"
            
        return "UNKNOWN"
    
    @staticmethod
    def validate_symbol_format(symbol: str) -> Tuple[bool, str]:
        """
        Validate if a symbol has a proper format for Indian markets.
        
        Args:
            symbol: Symbol to validate
            
        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        if not symbol:
            return False, "Symbol cannot be empty"
            
        symbol = symbol.upper().strip()
        
        # Check length
        if len(symbol) > 20:  # Reasonable max length
            return False, "Symbol too long (max 20 characters)"
            
        if len(symbol) < 1:
            return False, "Symbol too short"
            
        # Check for valid characters
        if not re.match(r'^[A-Z0-9^.\-&]{1,20}$', symbol):
            return False, "Symbol contains invalid characters (only A-Z, 0-9, ^, ., -, & allowed)"
            
        # Additional validation for different formats
        if symbol.startswith("^"):
            # Index symbol validation
            if not re.match(r'^\^[A-Z0-9]{3,10}$', symbol):
                return False, "Invalid index symbol format"
        elif symbol.endswith((".NS", ".BO")):
            # Yahoo Finance format validation
            base = symbol[:-3]
            if not re.match(r'^[A-Z0-9&-]{1,10}$', base):
                return False, "Invalid base symbol in Yahoo Finance format"
        elif symbol.isdigit():
            # BSE numerical code validation
            if len(symbol) != 6:
                return False, "BSE numerical codes should be 6 digits"
        else:
            # Regular symbol validation
            if not re.match(r'^[A-Z0-9&-]{1,10}$', symbol):
                return False, "Invalid symbol format for Indian equity"
                
        return True, ""
    
    @staticmethod
    def get_provider_symbol(symbol: str, provider: str) -> str:
        """
        Get symbol formatted for specific data provider.
        
        Args:
            symbol: Raw or formatted symbol
            provider: Provider name ('yahoo', 'alpha_vantage', 'polygon', etc.)
            
        Returns:
            str: Symbol formatted for the provider
        """
        if not symbol:
            return symbol
            
        provider = provider.lower().strip()
        
        if provider in ["yahoo", "yahoo_finance", "yfinance"]:
            return IndianEquitySymbolNormalizer.normalize_for_yahoo_finance(symbol)
        elif provider in ["alpha_vantage", "alphavantage"]:
            return IndianEquitySymbolNormalizer.normalize_for_alpha_vantage(symbol)
        elif provider in ["polygon", "finnhub"]:
            # These providers have their own formats
            if provider == "polygon":
                return IndianEquitySymbolNormalizer.normalize_for_polygon(symbol)
            else:  # finnhub
                return IndianEquitySymbolNormalizer.normalize_for_finnhub(symbol)
        else:
            # Default to base symbol
            return IndianEquitySymbolNormalizer.get_base_symbol(symbol)
    
    @staticmethod
    def normalize_for_polygon(symbol: str) -> str:
        """
        Normalize symbol for Polygon.io (uses base symbols with exchange prefix).
        
        Args:
            symbol: Symbol to normalize
            
        Returns:
            str: Symbol formatted for Polygon
        """
        if not symbol:
            return symbol
            
        symbol = symbol.upper().strip()
        
        # Get base symbol
        base_symbol = IndianEquitySymbolNormalizer.get_base_symbol(symbol)
        
        # Handle indices
        if symbol.startswith("^"):
            polygon_index_map = {
                "^NSEI": "I:NIFTY",
                "^BSESN": "I:SENSEX",
                "^INDIAVIX": "I:INDIAVIX",
                "^NSEBANK": "I:BANKNIFTY"
            }
            return polygon_index_map.get(symbol, f"I:{base_symbol}")
        
        # For regular stocks, Polygon might use exchange prefix
        exchange = IndianEquitySymbolNormalizer.detect_exchange(symbol)
        if exchange == "NSE":
            return f"NSE:{base_symbol}"
        elif exchange == "BSE":
            return f"BSE:{base_symbol}"
        else:
            return base_symbol
    
    @staticmethod
    def normalize_for_finnhub(symbol: str) -> str:
        """
        Normalize symbol for Finnhub (similar to Alpha Vantage).
        
        Args:
            symbol: Symbol to normalize
            
        Returns:
            str: Symbol formatted for Finnhub
        """
        # Finnhub uses similar format to Alpha Vantage for Indian stocks
        return IndianEquitySymbolNormalizer.normalize_for_alpha_vantage(symbol)
    
    @staticmethod
    def convert_bse_to_nse(bse_code: str) -> Optional[str]:
        """
        Convert BSE numerical code to NSE symbol.
        
        Args:
            bse_code: BSE numerical code
            
        Returns:
            Optional[str]: NSE symbol if mapping exists, None otherwise
        """
        if not bse_code or not bse_code.isdigit():
            return None
            
        return IndianEquitySymbolNormalizer.BSE_TO_NSE_MAPPING.get(bse_code)
    
    @staticmethod
    def convert_nse_to_bse(nse_symbol: str) -> Optional[str]:
        """
        Convert NSE symbol to BSE numerical code.
        
        Args:
            nse_symbol: NSE symbol
            
        Returns:
            Optional[str]: BSE code if mapping exists, None otherwise
        """
        if not nse_symbol:
            return None
            
        # Create reverse mapping
        nse_to_bse = {v: k for k, v in IndianEquitySymbolNormalizer.BSE_TO_NSE_MAPPING.items()}
        base_symbol = IndianEquitySymbolNormalizer.get_base_symbol(nse_symbol)
        return nse_to_bse.get(base_symbol)
    
    @staticmethod
    def get_alternative_symbols(symbol: str) -> Dict[str, str]:
        """
        Get alternative representations of the same symbol.
        
        Args:
            symbol: Input symbol
            
        Returns:
            Dict[str, str]: Dictionary with different format alternatives
        """
        if not symbol:
            return {}
            
        base_symbol = IndianEquitySymbolNormalizer.get_base_symbol(symbol)
        alternatives = {
            "base": base_symbol,
            "yahoo_nse": f"{base_symbol}.NS",
            "yahoo_bse": f"{base_symbol}.BO",
            "alpha_vantage": base_symbol,
            "polygon": f"NSE:{base_symbol}",
            "finnhub": base_symbol
        }
        
        # Add BSE code if available
        bse_code = IndianEquitySymbolNormalizer.convert_nse_to_bse(symbol)
        if bse_code:
            alternatives["bse_code"] = bse_code
            alternatives["yahoo_bse_code"] = f"{bse_code}.BO"
        
        # Add NSE symbol if input is BSE code
        if symbol.isdigit() and len(symbol) == 6:
            nse_symbol = IndianEquitySymbolNormalizer.convert_bse_to_nse(symbol)
            if nse_symbol:
                alternatives["nse_equivalent"] = nse_symbol
                alternatives["yahoo_nse_equivalent"] = f"{nse_symbol}.NS"
        
        return alternatives
    
    @staticmethod
    def get_symbol_metadata(symbol: str) -> Dict[str, Any]:
        """
        Get comprehensive metadata about a symbol.
        
        Args:
            symbol: Symbol to analyze
            
        Returns:
            Dict[str, Any]: Metadata including validation, exchange, alternatives
        """
        if not symbol:
            return {"error": "Empty symbol"}
            
        is_valid, error_msg = IndianEquitySymbolNormalizer.validate_symbol_format(symbol)
        exchange = IndianEquitySymbolNormalizer.detect_exchange(symbol)
        base_symbol = IndianEquitySymbolNormalizer.get_base_symbol(symbol)
        alternatives = IndianEquitySymbolNormalizer.get_alternative_symbols(symbol)
        
        metadata = {
            "original_symbol": symbol,
            "base_symbol": base_symbol,
            "is_valid": is_valid,
            "validation_error": error_msg if not is_valid else None,
            "is_indian_symbol": IndianEquitySymbolNormalizer.is_indian_symbol(symbol),
            "detected_exchange": exchange,
            "symbol_type": "index" if symbol.startswith("^") else "equity",
            "alternatives": alternatives,
            "provider_formats": {
                "yahoo_finance": IndianEquitySymbolNormalizer.normalize_for_yahoo_finance(symbol),
                "alpha_vantage": IndianEquitySymbolNormalizer.normalize_for_alpha_vantage(symbol),
                "polygon": IndianEquitySymbolNormalizer.normalize_for_polygon(symbol),
                "finnhub": IndianEquitySymbolNormalizer.normalize_for_finnhub(symbol)
            }
        }
        
        return metadata
    
    @staticmethod
    def bulk_normalize(symbols: list, provider: str = "yahoo") -> Dict[str, Dict[str, str]]:
        """
        Normalize multiple symbols at once.
        
        Args:
            symbols: List of symbols to normalize
            provider: Target provider for normalization
            
        Returns:
            Dict[str, Dict[str, str]]: Mapping of original to normalized symbols with metadata
        """
        results = {}
        
        for symbol in symbols:
            try:
                normalized = IndianEquitySymbolNormalizer.get_provider_symbol(symbol, provider)
                is_valid, error_msg = IndianEquitySymbolNormalizer.validate_symbol_format(symbol)
                
                results[symbol] = {
                    "normalized": normalized,
                    "provider": provider,
                    "is_valid": is_valid,
                    "error": error_msg if not is_valid else None,
                    "exchange": IndianEquitySymbolNormalizer.detect_exchange(symbol)
                }
            except Exception as e:
                logger.warning(f"Error normalizing symbol {symbol}: {e}")
                results[symbol] = {
                    "normalized": symbol,
                    "provider": provider,
                    "is_valid": False,
                    "error": str(e),
                    "exchange": "UNKNOWN"
                }
        
        return results
