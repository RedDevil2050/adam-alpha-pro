"""
Safe Data Utilities for Indian Market Data Extraction
====================================================

This module provides safe utility functions for handling Indian market data extraction,
validation, and processing with proper error handling and data validation.
"""

import re
from typing import Any, Optional, Dict, Tuple, Union
from decimal import Decimal, InvalidOperation
from loguru import logger
from datetime import datetime


def safe_get_price(data: Dict[str, Any], symbol: str) -> Optional[float]:
    """
    Safely extract price from market data response.
    
    Args:
        data: Market data dictionary
        symbol: Stock symbol for logging
        
    Returns:
        Price as float or None if not found/invalid
    """
    try:
        # Try different common price field names
        price_fields = ['price', 'last_price', 'ltp', 'current_price', 'close', 'last']
        
        for field in price_fields:
            if field in data and data[field] is not None:
                price = float(data[field])
                if price > 0:  # Validate positive price
                    return price
                    
        # Try nested price fields
        if 'quote' in data and isinstance(data['quote'], dict):
            for field in price_fields:
                if field in data['quote']:
                    price = float(data['quote'][field])
                    if price > 0:
                        return price
                        
        logger.warning(f"No valid price found for {symbol} in data: {list(data.keys())}")
        return None
        
    except (ValueError, TypeError, KeyError) as e:
        logger.error(f"Error extracting price for {symbol}: {e}")
        return None


def safe_get_volume(data: Dict[str, Any], symbol: str) -> Optional[int]:
    """
    Safely extract volume from market data response.
    
    Args:
        data: Market data dictionary
        symbol: Stock symbol for logging
        
    Returns:
        Volume as int or None if not found/invalid
    """
    try:
        # Try different common volume field names
        volume_fields = ['volume', 'total_volume', 'day_volume', 'vol']
        
        for field in volume_fields:
            if field in data and data[field] is not None:
                volume = int(float(data[field]))
                if volume >= 0:  # Validate non-negative volume
                    return volume
                    
        # Try nested volume fields
        if 'quote' in data and isinstance(data['quote'], dict):
            for field in volume_fields:
                if field in data['quote']:
                    volume = int(float(data['quote'][field]))
                    if volume >= 0:
                        return volume
                        
        logger.warning(f"No valid volume found for {symbol} in data: {list(data.keys())}")
        return None
        
    except (ValueError, TypeError, KeyError) as e:
        logger.error(f"Error extracting volume for {symbol}: {e}")
        return None


def safe_get_float(data: Dict[str, Any], field: str, default: float = 0.0) -> float:
    """
    Safely extract float value from data dictionary.
    
    Args:
        data: Data dictionary
        field: Field name to extract
        default: Default value if extraction fails
        
    Returns:
        Float value or default
    """
    try:
        if field in data and data[field] is not None:
            return float(data[field])
        return default
    except (ValueError, TypeError):
        return default


def safe_numeric_compare(value1: Any, value2: Any, tolerance: float = 0.001) -> bool:
    """
    Safely compare two numeric values with tolerance.
    
    Args:
        value1: First value to compare
        value2: Second value to compare
        tolerance: Comparison tolerance for floating-point numbers
        
    Returns:
        True if values are numerically equal within tolerance
    """
    try:
        num1 = float(value1) if value1 is not None else 0.0
        num2 = float(value2) if value2 is not None else 0.0
        return abs(num1 - num2) <= tolerance
    except (ValueError, TypeError):
        return False


def safe_rsi_score(rsi_value: Any) -> float:
    """
    Convert RSI value to a normalized score (0-1).
    
    Args:
        rsi_value: RSI value (0-100)
        
    Returns:
        Normalized RSI score (0-1)
    """
    try:
        rsi = float(rsi_value) if rsi_value is not None else 50.0
        # Clamp RSI to valid range
        rsi = max(0.0, min(100.0, rsi))
        # Convert to 0-1 score (50 = neutral = 0.5)
        return rsi / 100.0
    except (ValueError, TypeError):
        return 0.5  # Neutral score if invalid


def validate_indian_market_data(data: Dict[str, Any], symbol: str) -> Tuple[bool, Optional[str]]:
    """
    Validate Indian market data for completeness and accuracy.
    
    Args:
        data: Market data dictionary
        symbol: Stock symbol for validation
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        # Check if data exists
        if not data or not isinstance(data, dict):
            return False, "No data provided or invalid data format"
            
        # Check for basic price data
        price = safe_get_price(data, symbol)
        if price is None:
            return False, "No valid price data found"
            
        # Validate price range for Indian stocks (₹1 to ₹100,000)
        if price < 1.0 or price > 100000.0:
            return False, f"Price {price} outside valid range for Indian stocks"
            
        # Check volume if present
        volume = safe_get_volume(data, symbol)
        if volume is not None and volume < 0:
            return False, "Negative volume not allowed"
            
        # Check for Indian stock symbol pattern
        if not _is_valid_indian_symbol(symbol):
            return False, f"Symbol {symbol} does not match Indian stock pattern"
            
        return True, None
        
    except Exception as e:
        logger.error(f"Error validating market data for {symbol}: {e}")
        return False, f"Validation error: {str(e)}"


def log_data_extraction_result(symbol: str, success: bool, data_source: str, 
                             price: Optional[float] = None, volume: Optional[int] = None):
    """
    Log the result of data extraction for monitoring and debugging.
    
    Args:
        symbol: Stock symbol
        success: Whether extraction was successful
        data_source: Source of the data (e.g., 'yahoo', 'alpha_vantage')
        price: Extracted price (if available)
        volume: Extracted volume (if available)
    """
    try:
        status = "SUCCESS" if success else "FAILED"
        log_msg = f"Data extraction {status} for {symbol} from {data_source}"
        
        if success and price is not None:
            log_msg += f" - Price: ₹{price:.2f}"
            if volume is not None:
                log_msg += f", Volume: {volume:,}"
                
        if success:
            logger.info(log_msg)
        else:
            logger.warning(log_msg)
            
    except Exception as e:
        logger.error(f"Error logging data extraction result: {e}")


def _is_valid_indian_symbol(symbol: str) -> bool:
    """
    Check if symbol matches Indian stock patterns.
    
    Args:
        symbol: Stock symbol to validate
        
    Returns:
        True if valid Indian symbol pattern
    """
    if not symbol or not isinstance(symbol, str):
        return False
        
    symbol = symbol.upper().strip()
    
    # Common Indian stock patterns
    patterns = [
        r'^[A-Z0-9&]+$',           # Basic NSE symbols (RELIANCE, HDFCBANK, etc.)
        r'^[A-Z0-9&]+\.NS$',       # Yahoo NSE format (RELIANCE.NS)
        r'^[A-Z0-9&]+\.BO$',       # Yahoo BSE format (RELIANCE.BO)
        r'^\d{6}$',                # BSE numerical codes (500325)
        r'^\^NSE[A-Z0-9]+$',       # NSE index symbols (^NSEI, ^NSEBANK)
        r'^\^BSE[A-Z0-9]+$',       # BSE index symbols (^BSESN)
        r'^(NIFTY|SENSEX|BANKNIFTY)$',  # Index names
    ]
    
    return any(re.match(pattern, symbol) for pattern in patterns)


def sanitize_market_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize market data by removing invalid values and normalizing fields.
    
    Args:
        data: Raw market data dictionary
        
    Returns:
        Sanitized market data dictionary
    """
    try:
        sanitized = {}
        
        for key, value in data.items():
            if value is None:
                continue
                
            # Handle numeric fields
            if key in ['price', 'volume', 'high', 'low', 'open', 'close', 'change']:
                try:
                    num_value = float(value)
                    if key == 'volume':
                        sanitized[key] = max(0, int(num_value))  # Volume must be non-negative integer
                    elif key in ['price', 'high', 'low', 'open', 'close']:
                        sanitized[key] = max(0.01, num_value)  # Prices must be positive
                    else:
                        sanitized[key] = num_value
                except (ValueError, TypeError):
                    continue
                    
            # Handle string fields
            elif isinstance(value, str):
                sanitized[key] = value.strip()
                
            # Handle other types as-is
            else:
                sanitized[key] = value
                
        return sanitized
        
    except Exception as e:
        logger.error(f"Error sanitizing market data: {e}")
        return data  # Return original data if sanitization fails
