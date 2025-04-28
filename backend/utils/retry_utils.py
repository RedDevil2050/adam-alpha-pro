import asyncio
import logging
import random
import functools
from typing import Any, Callable, TypeVar, cast, Optional

logger = logging.getLogger(__name__)

T = TypeVar('T')

def async_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    retry_exceptions: tuple = (Exception,),
    on_retry: Optional[Callable[[int, Exception], None]] = None
):
    """
    Decorator for asynchronous functions to retry on failure with exponential backoff.
    
    Args:
        max_retries: Maximum number of retries before giving up
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        backoff_factor: Multiplicative factor for delay after each retry
        jitter: Whether to add randomness to retry delays
        retry_exceptions: Exception types that should trigger a retry
        on_retry: Optional callback function to execute on each retry
    
    Returns:
        Decorated function that will retry on specified exceptions
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            retries = 0
            delay = base_delay
            
            while True:
                try:
                    return await func(*args, **kwargs)
                except retry_exceptions as e:
                    retries += 1
                    
                    # Check if we've reached max retries
                    if retries > max_retries:
                        logger.error(f"Max retries ({max_retries}) reached for {func.__name__}: {str(e)}")
                        raise
                    
                    # Calculate next delay with exponential backoff
                    if jitter:
                        # Add jitter (random factor between 0.8 and 1.2)
                        jitter_factor = random.uniform(0.8, 1.2)
                        current_delay = min(max_delay, delay * jitter_factor)
                    else:
                        current_delay = min(max_delay, delay)
                    
                    logger.warning(
                        f"Retry {retries}/{max_retries} for {func.__name__} after {current_delay:.2f}s: {str(e)}"
                    )
                    
                    # Call on_retry callback if provided
                    if on_retry:
                        on_retry(retries, e)
                    
                    # Wait before retry
                    await asyncio.sleep(current_delay)
                    
                    # Increase delay for next retry
                    delay = min(max_delay, delay * backoff_factor)
        
        return wrapper
    
    return decorator

def retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    retry_exceptions: tuple = (Exception,),
    on_retry: Optional[Callable[[int, Exception], None]] = None
):
    """
    Decorator for synchronous functions to retry on failure with exponential backoff.
    
    Args:
        max_retries: Maximum number of retries before giving up
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        backoff_factor: Multiplicative factor for delay after each retry
        jitter: Whether to add randomness to retry delays
        retry_exceptions: Exception types that should trigger a retry
        on_retry: Optional callback function to execute on each retry
    
    Returns:
        Decorated function that will retry on specified exceptions
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            delay = base_delay
            
            while True:
                try:
                    return func(*args, **kwargs)
                except retry_exceptions as e:
                    retries += 1
                    
                    # Check if we've reached max retries
                    if retries > max_retries:
                        logger.error(f"Max retries ({max_retries}) reached for {func.__name__}: {str(e)}")
                        raise
                    
                    # Calculate next delay with exponential backoff
                    if jitter:
                        # Add jitter (random factor between 0.8 and 1.2)
                        jitter_factor = random.uniform(0.8, 1.2)
                        current_delay = min(max_delay, delay * jitter_factor)
                    else:
                        current_delay = min(max_delay, delay)
                    
                    logger.warning(
                        f"Retry {retries}/{max_retries} for {func.__name__} after {current_delay:.2f}s: {str(e)}"
                    )
                    
                    # Call on_retry callback if provided
                    if on_retry:
                        on_retry(retries, e)
                    
                    # Wait before retry
                    import time
                    time.sleep(current_delay)
                    
                    # Increase delay for next retry
                    delay = min(max_delay, delay * backoff_factor)
        
        return wrapper
    
    return decorator

def is_rate_limit_error(e: Exception) -> bool:
    """
    Check if an exception indicates a rate limit error.
    
    Args:
        e: Exception to check
        
    Returns:
        True if this appears to be a rate limiting error
    """
    err_msg = str(e).lower()
    
    # Check for common rate limit indicators
    rate_limit_indicators = [
        'rate limit',
        'rate exceeded',
        'too many requests',
        '429',
        'throttle',
        'quota'
    ]
    
    for indicator in rate_limit_indicators:
        if indicator in err_msg:
            return True
    
    # Also check for specific HTTP status codes in exception message
    if '429' in err_msg:
        return True
        
    return False