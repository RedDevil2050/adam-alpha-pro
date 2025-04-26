from backend.utils.data_provider import fetch_price_alpha_vantage
import httpx
from bs4 import BeautifulSoup

async def run(symbol: str, results: dict = None) -> dict:
    """
    Stealth scrape via Tijori Finance if Alpha Vantage price is missing or invalid.
    """
    try:
        # 1) Primary: Alpha Vantage
        price = await fetch_price_alpha_vantage(symbol)
        # 2) Fallback: Tijori Finance web scrape
        if not price or price <= 0:
            url = f"https://www.tijorifinance.com/stock/{symbol.lower()}/"
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                # Hypothetical selector for price
                price_elem = soup.find('span', class_='price-text')
                if price_elem:
                    price = float(price_elem.text.replace(',', '').strip())
        # 3) No data
        if not price:
            return {'verdict': 'avoid', 'confidence': 0.2}
        # 4) Verdict & confidence
        verdict = 'strong_buy' if price > 200 else 'buy' if price > 100 else 'hold'
        confidence = round(min(price / 200, 1.0), 2)
        return {'verdict': verdict, 'confidence': confidence, 'price': price}
    except Exception as e:
        return {'verdict': 'avoid', 'confidence': 0.0, 'error': str(e)}
