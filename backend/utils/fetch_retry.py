import httpx
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from loguru import logger

@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(2),
    retry=retry_if_exception_type((httpx.RequestError, httpx.TimeoutException)),
    reraise=True
)
async def fetch_with_retry(url: str):
    async with httpx.AsyncClient(timeout=10) as client:
        logger.debug(f"Fetching URL: {url}")
        response = await client.get(url)
        response.raise_for_status()
        return response
