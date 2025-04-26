
import os, json, asyncio, httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from aiolimiter import AsyncLimiter
from circuitbreaker import circuit
from tenacity import retry, stop_after_attempt, wait_exponential
from bs4 import BeautifulSoup
from circuitbreaker import circuit
from tenacity import retry, stop_after_attempt, wait_exponential
from bs4 import BeautifulSoup  # fallback scraping
from circuitbreaker import circuit
from tenacity import retry, stop_after_attempt, wait_exponential
from backend.utils.cache_utils import cache_data_provider
from backend.config.settings import settings
from loguru import logger

# -------------  Rate‑Limiter (5 calls/min default) -------------
api_limiter = AsyncLimiter(max_rate=5, time_period=60)

def with_retry():
    return retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )

# ------------------- Alpha‑Vantage Fetchers --------------------

@cache_data_provider(ttl=60)
@with_retry()
async def fetch_price_point(symbol: str) -> dict:
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=5))
    @circuit(failure_threshold=2, recovery_timeout=60)
    async def _api_call(sym):
        async with api_limiter:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f'https://www.alphavantage.co/query', params={'function':'GLOBAL_QUOTE','symbol':sym,'apikey':settings.alpha_vantage_key})
                resp.raise_for_status()
                data = resp.json().get('Global Quote',{})
                return float(data.get('05. price', 0.0))
    try:
        price = await _api_call(symbol)
        if price and price>0: return price
    except Exception as e:
        logger.warning(f'API fetch failed for {symbol}, fallback to scraping: {e}')
    # Scraper fallback
    url = f'https://www.trendlyne.com/stock/{symbol}/'
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'html.parser')
    elem = soup.select_one('.stock-price')
    if not elem:
        raise RuntimeError('Trendlyne selector missing')  # surface to CI/alerts
    return float(elem.text.replace(',',''))
    # Dual-channel fallback: API + web scraper
    try:
        # API fetch logic (already present)
        pass
    except Exception:
        # Fallback to Trendlyne scraping
        url = f"https://www.trendlyne.com/stock/{symbol}/"
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.get(url)
        soup = BeautifulSoup(res.text, 'html.parser')
        price_elem = soup.select_one('.stock-price')
        if not price_elem:
            raise RuntimeError('Trendlyne selector missing')
        return float(price_elem.text.replace(',', ''))
    """Return { 'latestPrice': float }. Uses Alpha‑Vantage or 0 on fallback."""
    apikey = settings.alpha_vantage_key or "demo"
    url = "https://www.alphavantage.co/query"
    params = {"function": "GLOBAL_QUOTE", "symbol": symbol, "apikey": apikey}
    async with api_limiter:
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.get(url, params=params)
    if res.status_code != 200:
        logger.warning(f"Alpha Vantage error {res.status_code}")
        return {"latestPrice": 0.0}
    quote = res.json().get("Global Quote", {})
    return {"latestPrice": float(quote.get("05. price", 0.0))}

# ------------------- EPS Fetch (Overview endpoint) -------------
@cache_data_provider(ttl=86400)
@with_retry()
async def fetch_eps(symbol: str) -> float:
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=5))
    @circuit(failure_threshold=2, recovery_timeout=60)
    async def _api_eps(sym):
        async with api_limiter:
            async with httpx.AsyncClient(timeout=10) as client:
                res = await client.get('https://www.alphavantage.co/query', params={
                    'function':'OVERVIEW', 'symbol': sym, 'apikey': settings.alpha_vantage_key
                })
                res.raise_for_status()
                return float(res.json().get('EPS', 0.0))
    try:
        eps = await _api_eps(symbol)
        if eps and eps>0: return eps
    except Exception as e:
        logger.warning(f'API EPS fetch failed for {symbol}, fallback to scraping: {e}')
    # Scraper fallback for EPS
    url = f'https://www.trendlyne.com/stock/{symbol}/analytics/'
    async with httpx.AsyncClient(timeout=10) as client:
        res = await client.get(url)
        res.raise_for_status()
    soup = BeautifulSoup(res.text, 'html.parser')
    eps_elem = soup.select_one('.eps-value')
    if not eps_elem:
        raise RuntimeError('Trendlyne EPS selector missing')
    return float(eps_elem.text)
    apikey = settings.alpha_vantage_key or "demo"
    url = "https://www.alphavantage.co/query"
    params = {"function": "OVERVIEW", "symbol": symbol, "apikey": apikey}
    async with api_limiter:
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.get(url, params=params)
    if res.status_code != 200:
        return 0.0
    return float(res.json().get("EPS", 0.0))

# ------------------- Price Series (TIME_SERIES_DAILY) ---------
@cache_data_provider(ttl=900)
@with_retry()
async def fetch_price_series(symbol: str) -> list[float]:
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=5))
    @circuit(failure_threshold=2, recovery_timeout=60)
    async def _api_series(sym):
        async with api_limiter:
            async with httpx.AsyncClient(timeout=10) as client:
                res = await client.get('https://www.alphavantage.co/query', params={
                    'function':'TIME_SERIES_DAILY_ADJUSTED', 'symbol': sym, 'apikey': settings.alpha_vantage_key
                })
                res.raise_for_status()
                data = res.json().get('Time Series (Daily)', {})
                return [float(v['4. close']) for v in data.values()]
    try:
        series = await _api_series(symbol)
        if series: return series
    except Exception as e:
        logger.warning(f'API series fetch failed for {symbol}, fallback to scraping: {e}')
    # Scraper fallback for series
    url = f'https://www.trendlyne.com/stock/{symbol}/price/'
    async with httpx.AsyncClient(timeout=10) as client:
        res = await client.get(url)
        res.raise_for_status()
    soup = BeautifulSoup(res.text, 'html.parser')
    elems = soup.select('.price-history .close-price')
    if not elems:
        raise RuntimeError('Trendlyne series selector missing')
    return [float(e.text.replace(',','')) for e in elems]
    apikey = settings.alpha_vantage_key or "demo"
    url = "https://www.alphavantage.co/query"
    params = {"function": "TIME_SERIES_DAILY", "symbol": symbol, "apikey": apikey, "outputsize": "compact"}
    async with api_limiter:
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.get(url, params=params)
    if res.status_code != 200:
        return []
    ts = res.json().get("Time Series (Daily)", {})
    prices = [float(v["4. close"]) for _, v in sorted(ts.items())]
    return prices[-60:]  # last 60 closes

async def fetch_gdp_growth(country_code: str = "IND") -> float | None:
    """
    Fetches latest annual GDP growth (%) from World Bank.
    """
    import httpx
    url = (
        f"http://api.worldbank.org/v2/country/{country_code}"
        "/indicator/NY.GDP.MKTP.KD.ZG?format=json&per_page=1"
    )
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
    if resp.status_code == 200:
        data = resp.json()
        try:
            return float(data[1][0].get("value"))
        except:
            return None
    return None

async def fetch_inflation_rate(country_code: str = "IND") -> float | None:
    """
    Fetches latest annual inflation rate (%) from World Bank.
    """
    import httpx
    url = (
        f"http://api.worldbank.org/v2/country/{country_code}"
        "/indicator/FP.CPI.TOTL.ZG?format=json&per_page=1"
    )
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
    if resp.status_code == 200:
        data = resp.json()
        try:
            return float(data[1][0].get("value"))
        except:
            return None
    return None

async def fetch_interest_rate(country_code: str = "IND") -> float | None:
    """
    Fetches latest policy interest rate (%) (using World Bank proxy).
    """
    import httpx
    url = (
        f"http://api.worldbank.org/v2/country/{country_code}"
        "/indicator/FR.INR.RINR?format=json&per_page=1"
    )
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
    if resp.status_code == 200:
        data = resp.json()
        try:
            return float(data[1][0].get("value"))
        except:
            return None
    return None

