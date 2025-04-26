
import os

def generate_stealth_agents(project_root: str):
    """
    Populates all stealth agents with dual-channel async scraping logic.
    """
    stealth_map = {
        'backend/agents/stealth/moneycontrol_agent.py': '''
import asyncio
import httpx
from bs4 import BeautifulSoup

async def fetch_primary(symbol: str) -> dict:
    url = f"https://www.moneycontrol.com/india/stockpricequote/pharmaceuticals/mankindpharma/{symbol}"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        price = soup.select_one('div.pcst_price div.Prcd')
        return {'source': 'moneycontrol', 'price': float(price.text.replace(',', ''))}

async def fetch_fallback(symbol: str) -> dict:
    import yfinance as yf
    ticker = yf.Ticker(symbol + '.NS')
    data = ticker.history(period='1d')
    price = data['Close'].iloc[-1]
    return {'source': 'yahoo', 'price': float(price)}

async def run(symbol: str, agent_outputs: dict) -> dict:
    for fetch in (fetch_primary, fetch_fallback):
        try:
            result = await fetch(symbol)
            return {'symbol': symbol, **result}
        except Exception:
            continue
    return {'symbol': symbol, 'source': None, 'price': None, 'error': 'Failed to fetch'}
''',

        'backend/agents/stealth/tradingview_agent.py': '''
import asyncio
import httpx
from bs4 import BeautifulSoup

async def fetch_primary(symbol: str) -> dict:
    api = f"https://symbol-search.tradingview.com/symbol_search/?text={symbol}&exchange=NASDAQ"
    async with httpx.AsyncClient(timeout=10) as client:
        res = await client.get(api)
        data = res.json()[0]
        return {'source': 'tradingview', 'symbol_full': data['symbol']}

async def fetch_fallback(symbol: str) -> dict:
    import yfinance as yf
    ticker = yf.Ticker(symbol + '.NS')
    info = ticker.info
    return {'source': 'yahoo', 'longName': info.get('longName')}

async def run(symbol: str, agent_outputs: dict) -> dict:
    for fn in (fetch_primary, fetch_fallback):
        try:
            return await fn(symbol)
        except Exception:
            continue
    return {'symbol': symbol, 'error': 'Fetch failed'}
''',

        'backend/agents/stealth/tickertape_agent.py': '''
import asyncio
import httpx
from bs4 import BeautifulSoup

async def fetch_primary(symbol: str) -> dict:
    url = f"https://www.tickertape.in/symbol/{symbol}.NS"
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, 'html.parser')
        price = soup.select_one('span.price___3HQyA')
        return {'source': 'tickertape', 'price': float(price.text)}

async def fetch_fallback(symbol: str) -> dict:
    import yfinance as yf
    price = yf.Ticker(symbol + '.NS').history(period='1d')['Close'].iloc[-1]
    return {'source': 'yahoo', 'price': float(price)}

async def run(symbol: str, agent_outputs: dict) -> dict:
    for fn in (fetch_primary, fetch_fallback):
        try:
            return await fn(symbol)
        except Exception:
            continue
    return {'symbol': symbol, 'error': 'All fetch attempts failed'}
''',

        'backend/agents/stealth/stockedge_agent.py': '''
import asyncio
import httpx
from bs4 import BeautifulSoup

async def fetch_primary(symbol: str) -> dict:
    url = f"https://stockedge.com/symbols/{symbol}.NS"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        soup = BeautifulSoup(resp.text, 'html.parser')
        kmc = soup.select_one('span.current-price')
        return {'source': 'stockedge', 'price': float(kmc.text.replace(',', ''))}

async def fetch_fallback(symbol: str) -> dict:
    import yfinance as yf
    data = yf.Ticker(symbol + '.NS').history(period='1d')
    return {'source': 'yahoo', 'price': float(data['Close'].iloc[-1])}

async def run(symbol: str, agent_outputs: dict) -> dict:
    for fn in (fetch_primary, fetch_fallback):
        try:
            return await fn(symbol)
        except Exception:
            continue
    return {'symbol': symbol, 'error': 'Failed'}
''',

        'backend/agents/stealth/trendlyne_agent.py': '''
import asyncio
import httpx
from bs4 import BeautifulSoup

async def fetch_primary(symbol: str) -> dict:
    url = f"https://trendlyne.com/equity/{symbol}.NS/"
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url)
        soup = BeautifulSoup(r.text, 'html.parser')
        score = soup.select_one('div.esg-score')
        return {'source': 'trendlyne', 'esg': float(score.text)}

async def fetch_fallback(symbol: str) -> dict:
    import yfinance as yf
    df = yf.Ticker(symbol + '.NS').sustainability
    return {'source': 'yahoo', 'esg': df['Value'].mean()}

async def run(symbol: str, agent_outputs: dict) -> dict:
    for fn in (fetch_primary, fetch_fallback):
        try:
            return await fn(symbol)
        except Exception:
            continue
    return {'symbol': symbol, 'error': 'No data'}
''',

        'backend/agents/stealth/zerodha_agent.py': '''
import asyncio
import httpx

async def fetch_primary(symbol: str) -> dict:
    api = f"https://api.kite.trade/quote?i={symbol.upper()}"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(api)
        data = resp.json()
        return {'source': 'zerodha', 'last_price': data.get('last_price')}

async def fetch_fallback(symbol: str) -> dict:
    import yfinance as yf
    price = yf.Ticker(symbol + '.NS').history(period='1d')['Close'].iloc[-1]
    return {'source': 'yahoo', 'price': float(price)}

async def run(symbol: str, agent_outputs: dict) -> dict:
    for fn in (fetch_primary, fetch_fallback):
        try:
            return await fn(symbol)
        except Exception:
            continue
    return {'symbol': symbol, 'error': 'Zerodha fetch failed'}
'''
    }

    for rel_path, code in stealth_map.items():
        full_path = os.path.join(project_root, rel_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w') as f:
            f.write(code.strip())
        print(f"Populated {rel_path}")

if __name__ == "__main__":
    generate_stealth_agents(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
