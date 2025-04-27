from functools import wraps
from typing import List
from backend.exceptions import ValidationError

def validate_input(min_symbols: int = 1, max_symbols: int = 100):
    """Decorator to validate input parameters"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract symbols from args/kwargs
            symbols = args[1] if len(args) > 1 else kwargs.get('symbols')
            
            if not isinstance(symbols, list):
                raise ValidationError("Symbols must be a list")
                
            if len(symbols) < min_symbols:
                raise ValidationError(f"At least {min_symbols} symbols required")
                
            if len(symbols) > max_symbols:
                raise ValidationError(f"Maximum {max_symbols} symbols allowed")
                
            return await func(*args, **kwargs)
        return wrapper
    return decorator
