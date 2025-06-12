"""
Safe Data Extraction Utilities for Stealth Agents
================================================

Utility functions to prevent NoneType comparison errors and ensure
robust data handling across all stealth agents.
"""

import re
from typing import Optional, Union, Dict, Any
from loguru import logger


def safe_numeric_compare(value: Optional[Union[int, float]], threshold: Union[int, float], default: float = 0.0) -> bool:
    """
    Safely compare potentially None values with a threshold.
    
    Args:
        value: The value to compare (may be None)
        threshold: The threshold to compare against
        default: Default value to use if value is None
        
    Returns:
        bool: Result of comparison
    """
    if value is None:
        return default > threshold
    try:
        return float(value) > threshold
    except (ValueError, TypeError):
        return default > threshold


def safe_get_price(data: Dict[str, Any], symbol: str = "unknown") -> Optional[float]:
    """
    Safely extract price from data dictionary.
    
    Args:
        data: Data dictionary containing price information
        symbol: Stock symbol for logging purposes
        
    Returns:
        float or None: Extracted price or None if not found
    """
    if not isinstance(data, dict):
        return None
    
    price_fields = ['price', 'current_price', 'last_price', 'ltp', 'close', 'last', 'value', 'quote']
    
    for field in price_fields:
        if field in data and data[field] is not None:
            try:
                # Handle string prices with currency symbols
                if isinstance(data[field], str):
                    clean_price = data[field].replace('₹', '').replace('$', '').replace(',', '').strip()
                    if clean_price and re.match(r'^\d+\.?\d*$', clean_price):
                        price = float(clean_price)
                        # Reasonable price range for Indian stocks
                        if 0.01 <= price <= 100000:
                            return price
                else:
                    price = float(data[field])
                    if 0.01 <= price <= 100000:
                        return price
            except (ValueError, TypeError):
                continue
    
    return None


def safe_get_volume(data: Dict[str, Any], symbol: str = "unknown") -> Optional[int]:
    """
    Safely extract volume from data dictionary.
    
    Args:
        data: Data dictionary containing volume information
        symbol: Stock symbol for logging purposes
        
    Returns:
        int or None: Extracted volume or None if not found
    """
    if not isinstance(data, dict):
        return None
    
    volume_fields = ['volume', 'trade_volume', 'vol', 'total_volume']
    
    for field in volume_fields:
        if field in data and data[field] is not None:
            try:
                # Handle string volumes with suffixes (K, M, B)
                if isinstance(data[field], str):
                    volume_str = data[field].replace(',', '').strip().upper()
                    
                    if 'K' in volume_str:
                        base_vol = float(volume_str.replace('K', ''))
                        volume = int(base_vol * 1000)
                    elif 'M' in volume_str:
                        base_vol = float(volume_str.replace('M', ''))
                        volume = int(base_vol * 1000000)
                    elif 'B' in volume_str:
                        base_vol = float(volume_str.replace('B', ''))
                        volume = int(base_vol * 1000000000)
                    else:
                        if re.match(r'^\d+$', volume_str):
                            volume = int(volume_str)
                        else:
                            continue
                else:
                    volume = int(float(data[field]))
                
                # Reasonable volume range
                if 0 <= volume <= 1000000000:
                    return volume
                    
            except (ValueError, TypeError):
                continue
    
    return None


def safe_get_float(data: Dict[str, Any], key: str, default: float = 0.0) -> float:
    """
    Safely extract a float value from data dictionary.
    
    Args:
        data: Data dictionary
        key: Key to extract
        default: Default value if key not found or invalid
        
    Returns:
        float: Extracted value or default
    """
    if not isinstance(data, dict) or key not in data or data[key] is None:
        return default
    
    try:
        if isinstance(data[key], str):
            # Clean string numbers
            clean_val = data[key].replace(',', '').replace('%', '').strip()
            return float(clean_val)
        else:
            return float(data[key])
    except (ValueError, TypeError):
        return default


def safe_percentage_to_float(value: Optional[Union[str, float]], default: float = 0.0) -> float:
    """
    Safely convert percentage string to float.
    
    Args:
        value: Percentage value (e.g., "5.2%" or 5.2)
        default: Default value if conversion fails
        
    Returns:
        float: Converted percentage as decimal (e.g., 0.052 for "5.2%")
    """
    if value is None:
        return default
    
    try:
        if isinstance(value, str):
            clean_val = value.replace('%', '').replace(',', '').strip()
            return float(clean_val) / 100.0
        else:
            # Assume it's already a decimal if it's a number
            return float(value)
    except (ValueError, TypeError):
        return default


def safe_rsi_score(rsi: Optional[float], default_score: float = 0.0) -> float:
    """
    Safely calculate RSI-based score.
    
    Args:
        rsi: RSI value (0-100)
        default_score: Default score if RSI is None
        
    Returns:
        float: Score adjustment based on RSI
    """
    if rsi is None:
        return default_score
    
    try:
        rsi_val = float(rsi)
        if 30 <= rsi_val <= 70:  # Neutral zone
            return 0.05
        elif rsi_val < 30:  # Oversold - potential buy
            return 0.15
        elif rsi_val > 70:  # Overbought - potential sell
            return -0.1
        else:
            return default_score
    except (ValueError, TypeError):
        return default_score


def validate_indian_market_data(price: Optional[float], volume: Optional[int], symbol: str) -> Dict[str, Any]:
    """
    Validate data specifically for Indian market constraints.
    
    Args:
        price: Stock price
        volume: Trading volume
        symbol: Stock symbol
        
    Returns:
        dict: Validation result with issues and confidence
    """
    validation_result = {
        'is_valid': True,
        'confidence': 1.0,
        'issues': []
    }
    
    # Price validation
    if price is None:
        validation_result['is_valid'] = False
        validation_result['confidence'] *= 0.0
        validation_result['issues'].append('Missing price data')
    elif price <= 0:
        validation_result['is_valid'] = False
        validation_result['confidence'] *= 0.1
        validation_result['issues'].append('Invalid price (≤ 0)')
    elif price > 50000:  # Very high price for Indian stocks
        validation_result['confidence'] *= 0.7
        validation_result['issues'].append('Unusually high price')
    elif price < 1:  # Very low price
        validation_result['confidence'] *= 0.8
        validation_result['issues'].append('Very low price stock')
    
    # Volume validation
    if volume is None:
        validation_result['confidence'] *= 0.8
        validation_result['issues'].append('Missing volume data')
    elif volume == 0:
        validation_result['confidence'] *= 0.6
        validation_result['issues'].append('Zero volume')
    elif volume > 100000000:  # Very high volume
        validation_result['confidence'] *= 0.9
        validation_result['issues'].append('Unusually high volume')
    
    return validation_result


def log_data_extraction_result(source: str, symbol: str, price: Optional[float], 
                             volume: Optional[int], success: bool) -> None:
    """
    Log the result of data extraction for monitoring.
    
    Args:
        source: Data source name
        symbol: Stock symbol
        price: Extracted price
        volume: Extracted volume
        success: Whether extraction was successful
    """
    if success:
        logger.debug(f"✅ {source}: {symbol} - Price: ₹{price}, Volume: {volume:,}" if volume else f"✅ {source}: {symbol} - Price: ₹{price}")
    else:
        logger.warning(f"❌ {source}: {symbol} - Failed to extract valid data")
