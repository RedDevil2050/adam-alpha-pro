# backend/utils/http_utils.py
import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    wait_exponential,
    stop_after_attempt,
)


async def fetch_json_with_retry(
    url: str,
    params: dict = None,
    headers: dict = None,
    timeout: int = 10,
    max_attempts: int = 5,
) -> dict:
    """
    Fetch JSON data from a URL with retries and exponential backoff using HTTPX and Tenacity.
    """
    retrying = AsyncRetrying(
        retry=retry_if_exception_type(httpx.HTTPError),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        stop=stop_after_attempt(max_attempts),
    )
    async for attempt in retrying:
        with attempt:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                return response.json()


async def fetch_text_with_retry(
    url: str,
    params: dict = None,
    headers: dict = None,
    timeout: int = 10,
    max_attempts: int = 5,
) -> str:
    """
    Fetch text content from a URL with retries and exponential backoff using HTTPX and Tenacity.
    """
    retrying = AsyncRetrying(
        retry=retry_if_exception_type(httpx.HTTPError),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        stop=stop_after_attempt(max_attempts),
    )
    async for attempt in retrying:
        with attempt:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                return response.text
