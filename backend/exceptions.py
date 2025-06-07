"""
Custom exceptions for the Zion market analysis system.
"""


class ValidationError(Exception):
    """Custom validation error for the Zion system"""
    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class SymbolValidationError(ValidationError):
    """Specific error for symbol validation"""
    pass


class ProviderError(Exception):
    """Error related to data providers"""
    def __init__(self, provider: str, message: str, details: dict = None):
        self.provider = provider
        self.message = message
        self.details = details or {}
        super().__init__(f"[{provider}] {message}")


class RateLimitError(Exception):
    """Error when hitting API rate limits"""
    def __init__(self, provider: str, retry_after: int = None):
        self.provider = provider
        self.retry_after = retry_after
        message = f"Rate limit exceeded for {provider}"
        if retry_after:
            message += f". Retry after {retry_after} seconds"
        super().__init__(message)


# Import pydantic ValidationError for compatibility
try:
    from pydantic import ValidationError as PydanticValidationError
except ImportError:
    PydanticValidationError = ValidationError


__all__ = [
    'ValidationError',
    'SymbolValidationError', 
    'ProviderError',
    'RateLimitError',
    'PydanticValidationError'
]
