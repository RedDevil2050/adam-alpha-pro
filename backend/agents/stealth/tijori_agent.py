from backend.agents.stealth.base import StealthAgentBase
from backend.utils.data_provider import fetch_price_alpha_vantage
import httpx
from bs4 import BeautifulSoup
from loguru import logger

agent_name = "tijori_agent"


class TijoriAgent(StealthAgentBase):
    async def _execute(self, symbol: str, agent_outputs: dict) -> dict:
        try:
            # 1) Primary: Alpha Vantage
            price_data = await fetch_price_alpha_vantage(symbol)
            
            # Extract numeric price from response
            price = None
            if isinstance(price_data, dict) and 'price' in price_data:
                price = price_data['price']
            elif isinstance(price_data, (int, float)):
                price = price_data
            
            # 2) Fallback: Tijori Finance web scrape
            if not price or not isinstance(price, (int, float)) or price <= 0:
                data = await self._fetch_stealth_data(symbol)
                if data and 'price' in data:
                    price = data['price']

            # 3) No data
            if not price or not isinstance(price, (int, float)):
                return self._error_response(symbol, "No price data available")

            # 4) Calculate verdict and confidence
            verdict = self._get_verdict(price)
            confidence = self._calculate_confidence(price)

            return {
                "symbol": symbol,
                "verdict": verdict,
                "confidence": confidence,
                "value": price,
                "details": {"price": price, "source": "tijori"},
                "error": None,
                "agent_name": agent_name
            }

        except Exception as e:
            logger.error(f"Tijori analysis error: {e}")
            return self._error_response(symbol, str(e))

    async def _fetch_stealth_data(self, symbol: str) -> dict:
        url = f"https://www.tijorifinance.com/stock/{symbol.lower()}/"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            price_elem = soup.find("span", class_="price-text")
            if price_elem:
                try:
                    price = float(price_elem.text.replace(",", "").strip())
                    return {"price": price}
                except (ValueError, TypeError):
                    pass
        return {}

    def _get_verdict(self, price: float) -> str:
        if price > 200:
            return "STRONG_BUY"
        elif price > 100:
            return "BUY"
        return "HOLD"

    def _calculate_confidence(self, price: float) -> float:
        return round(min(price / 200, 1.0), 2)

    async def execute(self, symbol: str, agent_outputs: dict = {}) -> dict:
        """Public method to execute the agent's logic."""
        return await self._execute(symbol, agent_outputs)


async def run(symbol: str, agent_outputs: dict = {}) -> dict:
    agent = TijoriAgent()
    return await agent.execute(symbol, agent_outputs=agent_outputs)
