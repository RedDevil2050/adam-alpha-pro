import httpx
from bs4 import BeautifulSoup
from backend.config.settings import settings
from backend.utils.cache_utils import redis_client
from backend.utils.data_provider import fetch_alpha_vantage
from backend.utils.progress_tracker import ProgressTracker

# Shared progress tracker instance
tracker = ProgressTracker(filepath="backend/utils/progress.json")

async def fetch_esg_breakdown(symbol: str) -> dict:
    """
    Fetch ESG composite and sub-scores via API first, then fallback scrape.
    Returns dict with keys: composite, environmental, social, governance.
    """
    # 1) API fetch (hypothetical ESG endpoint)
    try:
        data = await fetch_alpha_vantage('query', {'function': 'ESG', 'symbol': symbol, 'apikey': settings.alpha_vantage_key})
        return {
            'composite': float(data.get('ESGScore', 0.0)),
            'environmental': float(data.get('EnvironmentalScore', 0.0)),
            'social': float(data.get('SocialScore', 0.0)),
            'governance': float(data.get('GovernanceScore', 0.0))
        }
    except Exception:
        pass

    try:
        url = f"https://example.com/esg/{symbol}"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
        soup = BeautifulSoup(resp.text, 'html.parser')
        score_elem = soup.select_one('.esg-composite-score')
        if score_elem:
            composite = float(score_elem.text)
            return {'composite': composite, 'environmental': None, 'social': None, 'governance': None}
    except Exception:
        pass

    return {}
