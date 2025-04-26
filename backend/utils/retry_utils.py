import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from functools import wraps
from loguru import logger

DEFAULT_RETRY_EXCEPTIONS = (httpx.RequestError, httpx.TimeoutException, httpx.HTTPStatusError)

def with_retry(attempts=3, wait_multiplier=1, wait_min=1, wait_max=10, exceptions=DEFAULT_RETRY_EXCEPTIONS):
    def decorator(func):
        @wraps(func)
        @retry(
            stop=stop_after_attempt(attempts),
            wait=wait_exponential(multiplier=wait_multiplier, min=wait_min, max=wait_max),
            retry=retry_if_exception_type(exceptions),
            reraise=True,
            before_sleep=lambda rs: logger.warning(f"Retrying {func.__name__} due to {rs.outcome.exception()}, attempt {rs.attempt_number}")
        )
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        return wrapper
    return decorator