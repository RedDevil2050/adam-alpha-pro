import httpx
from bs4 import BeautifulSoup
from backend.utils.cache_utils import redis_client
from backend.config.settings import settings
from backend.utils.progress_tracker import ProgressTracker

# Shared tracker instance
tracker = ProgressTracker(filepath="backend/utils/progress.json")


# Helper: fetch from AlphaVantage
async def fetch_alpha_events(symbol: str, function: str) -> dict:
    from backend.utils.data_provider import fetch_alpha_vantage

    try:
        data = await fetch_alpha_vantage(
            "query",
            {
                "function": function,
                "symbol": symbol,
                "apikey": settings.alpha_vantage_key,
            },
        )
        return data or {}
    except Exception:
        return {}
